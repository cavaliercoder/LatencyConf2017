# Configuring Timeouts In Micro-services

## Agenda


- Back story
- Goal
- Flow of load through system
- Why it matters

  - Architectures - Micro-services (pods), N-Tier, Monolith
  - Hidden timeouts

- Anatomy of a timeout

  - Requestor vs. Responder
  - Break down in components (TTFB, network, backends, transfer)

- Scenarios

  - Default high timeouts
  - Aggressive timeouts
    - healthy request failure
  - Equal timeouts
  - Bad request DOS

- One simple rule

  - Understanding max healthy operation
  - Understand load characterisation
  - Tradeoffs
    - Guaranteed delivery/consistency
    - Error rate/budget
    - Throughput

- Everything must be bounded


## Timeouts

How long a client waits for a response.

How long a server allows a request to run?

## Architectures

Even a simple web server will likely have a router in front and database behind.

N-Tier applications

Microservices

Container pods

## Example problems

- Client disconnects, request propagates, no request context to write to

- Tracing is difficult

! You can't control the user request timeout
