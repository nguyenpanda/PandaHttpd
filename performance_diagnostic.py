"""
Performance Diagnostic Tool for PandaHttpd
Helps identify bottlenecks in async vs sync implementations
"""

import asyncio
import time
from typing import Callable
import statistics


async def benchmark_endpoint(
    endpoint_func: Callable,
    num_requests: int = 100,
    concurrency: int = 10,
) -> dict:
    """Benchmark an endpoint with controlled concurrency"""
    
    async def single_request():
        start = time.perf_counter()
        try:
            if asyncio.iscoroutinefunction(endpoint_func):
                await endpoint_func()
            else:
                endpoint_func()
            duration = time.perf_counter() - start
            return {'success': True, 'duration': duration}
        except Exception as e:
            duration = time.perf_counter() - start
            return {'success': False, 'duration': duration, 'error': str(e)}
    
    # Run requests in batches with controlled concurrency
    all_results = []
    total_start = time.perf_counter()
    
    for i in range(0, num_requests, concurrency):
        batch_size = min(concurrency, num_requests - i)
        batch_tasks = [single_request() for _ in range(batch_size)]
        batch_results = await asyncio.gather(*batch_tasks)
        all_results.extend(batch_results)
    
    total_duration = time.perf_counter() - total_start
    
    # Calculate statistics
    durations = [r['duration'] for r in all_results if r['success']]
    successes = sum(1 for r in all_results if r['success'])
    
    return {
        'total_requests': num_requests,
        'successful': successes,
        'failed': num_requests - successes,
        'total_duration': total_duration,
        'requests_per_second': num_requests / total_duration,
        'avg_latency_ms': statistics.mean(durations) * 1000 if durations else 0,
        'median_latency_ms': statistics.median(durations) * 1000 if durations else 0,
        'min_latency_ms': min(durations) * 1000 if durations else 0,
        'max_latency_ms': max(durations) * 1000 if durations else 0,
        'p95_latency_ms': statistics.quantiles(durations, n=20)[18] * 1000 if len(durations) > 20 else 0,
    }


def print_benchmark_results(name: str, results: dict):
    """Pretty print benchmark results"""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"Total Requests:        {results['total_requests']}")
    print(f"Successful:            {results['successful']}")
    print(f"Failed:                {results['failed']}")
    print(f"Total Duration:        {results['total_duration']:.2f}s")
    print(f"Requests/Second:       {results['requests_per_second']:.2f}")
    print(f"\nLatency:")
    print(f"  Mean:                {results['avg_latency_ms']:.2f}ms")
    print(f"  Median:              {results['median_latency_ms']:.2f}ms")
    print(f"  Min:                 {results['min_latency_ms']:.2f}ms")
    print(f"  Max:                 {results['max_latency_ms']:.2f}ms")
    print(f"  P95:                 {results['p95_latency_ms']:.2f}ms")
    print(f"{'='*60}\n")


# ============ Performance Test Cases ============

# Simulated workloads
def cpu_bound_sync():
    """CPU-intensive synchronous work"""
    result = sum(i * i for i in range(1000))
    return result


async def cpu_bound_async():
    """CPU-intensive in async (BAD - blocks event loop!)"""
    result = sum(i * i for i in range(1000))
    return result


async def cpu_bound_async_proper(executor):
    """CPU-intensive properly offloaded to executor"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, cpu_bound_sync)
    return result


async def io_bound_async():
    """I/O-bound async operation"""
    await asyncio.sleep(0.01)  # Simulate I/O delay
    return "done"


def io_bound_sync():
    """I/O-bound synchronous operation (blocks thread)"""
    time.sleep(0.01)
    return "done"


async def minimal_async():
    """Minimal async overhead test"""
    return {"status": "ok"}


def minimal_sync():
    """Minimal sync overhead test"""
    return {"status": "ok"}


async def run_performance_tests():
    """Run comprehensive performance tests"""
    from concurrent.futures import ThreadPoolExecutor
    
    executor = ThreadPoolExecutor(max_workers=4)
    
    print("\n" + "="*60)
    print("  PandaHttpd Performance Diagnostics")
    print("="*60)
    print("\n📊 Running benchmarks...")
    
    # Test 1: Minimal overhead (shows async vs sync baseline)
    print("\n[1/6] Testing minimal overhead...")
    sync_minimal = await benchmark_endpoint(minimal_sync, num_requests=1000, concurrency=50)
    print_benchmark_results("Minimal Sync Endpoint", sync_minimal)
    
    async_minimal = await benchmark_endpoint(minimal_async, num_requests=1000, concurrency=50)
    print_benchmark_results("Minimal Async Endpoint", async_minimal)
    
    # Test 2: CPU-bound workload
    print("\n[2/6] Testing CPU-bound workload...")
    cpu_sync = await benchmark_endpoint(cpu_bound_sync, num_requests=100, concurrency=10)
    print_benchmark_results("CPU-Bound Sync (ThreadPool)", cpu_sync)
    
    cpu_async_bad = await benchmark_endpoint(cpu_bound_async, num_requests=100, concurrency=10)
    print_benchmark_results("CPU-Bound Async (BAD - blocks event loop)", cpu_async_bad)
    
    # Test 3: I/O-bound workload
    print("\n[3/6] Testing I/O-bound workload...")
    io_sync = await benchmark_endpoint(io_bound_sync, num_requests=100, concurrency=10)
    print_benchmark_results("I/O-Bound Sync (blocks thread)", io_sync)
    
    io_async = await benchmark_endpoint(io_bound_async, num_requests=100, concurrency=10)
    print_benchmark_results("I/O-Bound Async (non-blocking)", io_async)
    
    # Test 4: High concurrency I/O
    print("\n[4/6] Testing high concurrency I/O...")
    io_async_high = await benchmark_endpoint(io_bound_async, num_requests=1000, concurrency=100)
    print_benchmark_results("High Concurrency Async I/O (1000 req, 100 concurrent)", io_async_high)
    
    executor.shutdown(wait=True)
    
    # Summary
    print("\n" + "="*60)
    print("  📈 Performance Summary")
    print("="*60)
    print("\nKey Findings:")
    print(f"  Async overhead:        ~{(async_minimal['avg_latency_ms'] - sync_minimal['avg_latency_ms']):.3f}ms per request")
    print(f"  Sync RPS (minimal):    {sync_minimal['requests_per_second']:.0f} req/s")
    print(f"  Async RPS (minimal):   {async_minimal['requests_per_second']:.0f} req/s")
    print(f"\n  I/O Async advantage:   {(io_sync['total_duration'] / io_async['total_duration']):.1f}x faster")
    print(f"  High concurrency:      {io_async_high['requests_per_second']:.0f} req/s")
    
    print("\n💡 Recommendations:")
    if async_minimal['requests_per_second'] < sync_minimal['requests_per_second']:
        print("  ⚠️  Sync is faster for simple endpoints - this is NORMAL!")
        print("     Async shines with I/O operations and high concurrency")
    if cpu_async_bad['avg_latency_ms'] > cpu_sync['avg_latency_ms'] * 1.5:
        print("  ⚠️  CPU tasks should use ThreadPoolExecutor, not direct async")
    if io_async['requests_per_second'] > io_sync['requests_per_second'] * 2:
        print("  ✅ Async is significantly faster for I/O operations!")
    
    print("\n" + "="*60)


if __name__ == '__main__':
    asyncio.run(run_performance_tests())
