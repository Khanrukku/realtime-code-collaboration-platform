import asyncio
import statistics
import time
import uuid

import websockets


HOST = "ws://127.0.0.1:8000"

CLIENTS = 20
OPERATIONS_PER_CLIENT = 10


async def benchmark_client(client_number: int):
    room_id = f"benchmark-{client_number}-{uuid.uuid4().hex[:8]}"
    client_id = f"client-{client_number}"

    uri = f"{HOST}/ws/{room_id}/{client_id}"

    latencies = []

    async with websockets.connect(uri) as websocket:
        # Initial synchronization snapshot.
        snapshot = await websocket.recv()

        version = 0

        for operation_number in range(
            OPERATIONS_PER_CLIENT
        ):
            operation_id = (
                f"{client_number}-{operation_number}"
            )

            payload = (
                "{"
                f'"type":"insert",'
                f'"position":{operation_number},'
                f'"text":"x",'
                f'"base_version":{version},'
                f'"operation_id":"{operation_id}"'
                "}"
            )

            start = time.perf_counter()

            await websocket.send(payload)

            received_ack = False
            received_operation = False

            while not (
                received_ack
                and received_operation
            ):
                message = await websocket.recv()

                if '"type":"ack"' in message:
                    received_ack = True

                elif '"type":"operation"' in message:
                    received_operation = True

            latency_ms = (
                time.perf_counter() - start
            ) * 1000

            latencies.append(latency_ms)

            version += 1

    return latencies


async def main():
    start = time.perf_counter()

    results = await asyncio.gather(
        *[
            benchmark_client(client_number)
            for client_number in range(CLIENTS)
        ]
    )

    elapsed = time.perf_counter() - start

    latencies = [
        latency
        for client_latencies in results
        for latency in client_latencies
    ]

    operations = len(latencies)

    latencies_sorted = sorted(latencies)

    def percentile(percent):
        index = int(
            (percent / 100)
            * (len(latencies_sorted) - 1)
        )

        return latencies_sorted[index]

    print("===== WEBSOCKET BENCHMARK =====")
    print(f"Concurrent clients: {CLIENTS}")
    print(
        "Operations per client: "
        f"{OPERATIONS_PER_CLIENT}"
    )
    print(f"Total operations: {operations}")
    print(f"Total duration: {elapsed:.3f}s")

    print(
        "Operation throughput: "
        f"{operations / elapsed:.2f} ops/sec"
    )

    print(
        "Average round-trip latency: "
        f"{statistics.mean(latencies):.2f} ms"
    )

    print(
        "Median round-trip latency: "
        f"{statistics.median(latencies):.2f} ms"
    )

    print(
        f"P95 latency: "
        f"{percentile(95):.2f} ms"
    )

    print(
        f"P99 latency: "
        f"{percentile(99):.2f} ms"
    )

    print("===============================")


if __name__ == "__main__":
    asyncio.run(main())
