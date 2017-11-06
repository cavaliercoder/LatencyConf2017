# Configuring Timeouts In Micro-services

## Agenda

- What I mean by timeouts
- Which architectures it affects
- Example problems
  - Log/error info missing
- The Rule
- Demo fix
- Impact on Latency, Throughput and error rate
- Edge cases
  - Async backends
- Cancellation?
- Why long timeouts are deadly

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
