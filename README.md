This application is designed to generate CPU and memory load on a container.
Main purpose is to test and demostrate Kubernets resource requests and limits and pod autoscaler.

## API

The application exposes the following API:

- `/api/loadtest/v1/healthz`: health check, just answer with 200 OK
- `/api/loadtest/v1/mem/${SIZE}/${SECONDS}`: starts allocating `${SIZE}` MBytes of memory for `${SECONDS}` seconds
- `/api/loadtest/v1/cpu/${CPUS}/${SECONDS}`: spawn a number of child process using 100% oc CPU core for `${SECONDS}` seconds. The number of processes is defined by `${CPUS}`
- `/api/loadtest/v1/stats`: provies a json with stats about the processes

## Environments variables

* `START_CPU_PEAK_SEC`: if defined and > 0 the application will start using one or more core for the defined amount of seconds from the start of the application
* `START_CPU_PEAK_CORES`: the number of CPU core to use at the application startup

## Examples

- Start the loadtest app

```
$ oc new-app --name loadtest https://github.com/pbertera/hpa-demo/ --context-dir loadtest
```

- Check the build logs

```
$ oc logs bc/loadtest -f
```

- Once the build is completed, create the route

```
$ oc expose svc loadtest
```

- Test the application:

```
$ oc get pods
$ ROUTE_URL="http://$(oc get route loadtest -o jsonpath='{.spec.host}')"
```

- Health check:

```
$ curl -s ${ROUTE_URL}/api/loadtest/v1/healthz
{"health":"ok"}
```

- Check the stats

```
$ curl -s $ROUTE_URL/api/loadtest/v1/stats | jq
{
  "cores": 4,
  "hostname": "loadtest-5c6b969b4d-jh98n",
  "processes": [
    {
      "cpu": 0,
      "mem": 30.7421875,
      "pid": 1
    }
  ]
}
```

- Start 3 processes allocating 1 core of CPU for 60 seconds

```
$ curl -s $ROUTE_URL/api/loadtest/v1/cpu/3/60 | jq
{
  "message": "Allocated 3 cores for 60 seconds"
}

$ curl -s $ROUTE_URL/api/loadtest/v1/stats | jq
{
  "cores": 4,
  "hostname": "loadtest-5c6b969b4d-jh98n",
  "processes": [
    {
      "cpu": 0,
      "mem": 31.31640625,
      "pid": 1
    },
    {
      "cpu": 95.8,
      "mem": 24.6796875,
      "pid": 29
    },
    {
      "cpu": 97.8,
      "mem": 24.6796875,
      "pid": 30
    },
    {
      "cpu": 89.7,
      "mem": 24.6796875,
      "pid": 31
    }
  ]
}
```

- Allocate 500MB of memory for 60 seconds

```
$ curl -s $ROUTE_URL/api/loadtest/v1/mem/500/60 | jq
{
  "message": "Allocated 500 Megabytes for 60 seconds"
}

$ curl -s $ROUTE_URL/api/loadtest/v1/stats | jq
{
  "cores": 4,
  "hostname": "loadtest-5c6b969b4d-jh98n",
  "processes": [
    {
      "cpu": 0,
      "mem": 531.3515625,
      "pid": 1
    }
  ]
}
```

- Simulate 30 seconds startup spike of 2 CPU core:

```
$ oc set env deploy/loadtest START_CPU_PEAK_SEC=30 START_CPU_PEAK_CORES=2
$ curl -s $ROUTE_URL/api/loadtest/v1/stats | jq
{
  "cores": 4,
  "hostname": "loadtest-6755bcc8d9-xwrxj",
  "processes": [
    {
      "cpu": 0,
      "mem": 30.6875,
      "pid": 1
    },
    {
      "cpu": 69.6,
      "mem": 24.39453125,
      "pid": 19
    },
    {
      "cpu": 89.5,
      "mem": 24.40625,
      "pid": 20
    }
  ]
}
```

## Script demo 1

* Hands on on the HPA

*On the main terminal:*

Create a playground namespace

```
oc new-project hpa-demo
```

Start the loadtest app

```
oc new-app --name loadtest https://github.com/pbertera/hpa-demo/ --context-dir loadtest
```

Check the build logs

```
oc logs bc/loadtest -f
```

Once the build is completed, create the route

```
oc expose svc loadtest
```

Test the application:

```
oc get pods
ROUTE_URL="http://$(oc get route loadtest -o jsonpath='{.spec.host}')"
curl ${ROUTE_URL}/api/loadtest/v1/healthz
```

Set the resources on the application

```
oc set resources deployment loadtest --requests cpu=250m,memory=25Mi --limits cpu=1000m,memory=100Mi
```

Configure the HPA

```
oc autoscale deployment/loadtest --min 2 --max 10 --cpu-percent 50
```

Keep the relevant resources monitored

```
watch oc get hpa,podmetrics,pods
```

*On a different terminal:* start Apache Bench

```
ROUTE_URL="http://$(oc get route loadtest -o jsonpath='{.spec.host}')"
podman pull registry.access.redhat.com/ubi8/httpd-24
podman run -it --rm --name ab -e ROUTE_URL=$ROUTE_URL httpd /bin/bash -c "ab -c 200 -n 20000 ${ROUTE_URL}/api/loadtest/v1/healthz"
```

Let the application scale-up and scale-down

## Script demo 2

* Confirm that requests are needed to make the HPA working with the `Utilization` threshold type

*On the main terminal:* remove the CPU resource requests

```
oc edit deployment loadtest

[...]
        resources:
          limits:
            cpu: "1"
            memory: 100Mi
          requests:
            memory: 25Mi
[...]
```

Keep the relevant resources monitored

```
watch oc get hpa,podmetrics,pods
```

*On a different terminal:* start Apache Bench

```
podman run -it --rm --name ab -e ROUTE_URL=$ROUTE_URL httpd /bin/bash -c "ab -c 200 -n 20000 ${ROUTE_URL}/api/loadtest/v1/healthz"
```

The application should not scale-up

*On the main terminal:* change the threshold type to `AverageValue`

```
oc edit hpa loadtest

...
  metrics:
  - resource:
      name: cpu
      target:
        averageValue: 50
        type: AverageValue
...
```

Keep the relevant resources monitored

```
watch oc get hpa,podmetrics,pods
```

*On a different terminal:* start Apache Bench

```
podman run -it --rm --name ab -e ROUTE_URL=$ROUTE_URL httpd /bin/bash -c "ab -c 200 -n 20000 ${ROUTE_URL}/api/loadtest/v1/healthz"
```

Let the application scale-up and scale-down

## Script demo 3

* Scale on memory

*On the main terminal:* change the resource type to `memory`

```
oc edit hpa loadtest

...
  metrics:
  - resource:
      name: memory
      target:
        averageUtilization: 50
        type: Utilization
...
```

Set the limit resources on the application to avoid OOM-Kill

```
oc set resources deployment loadtest --requests cpu=250m,memory=200Mi --limits cpu=1000m,memory=1000M
```

Keep the relevant resources monitored

```
watch oc get hpa,podmetrics,pods
```

*On a different terminal:* create meory load allocating 500MB for 2 minutes

```
curl $ROUTE_URL/api/loadtest/v1/mem/500/120
```

Let the application scale-up and scale-down

## Script demo 4

* Startup CPU spike

*On the main terminal:* change the resource type to `cpu`

```
oc edit hpa loadtest

...
  metrics:
  - resource:
      name: cpu
      target:
        averageUtilization: 50
        type: Utilization
...
```

Set the resources on the application to request 1/4 of CPU core

```
oc set resources deployment loadtest --requests cpu=250m,memory=200Mi --limits cpu=1,memory=1000Mi
```

Configure the application to generate a CPU peak using 1 core for 5 minutes

```
oc set env deploy/loadtest START_CPU_PEAK_SEC=300 START_CPU_PEAK_CORES=1
```

## Cleanup

Remove the loadtest namespace

```
oc delete loadtest
```
