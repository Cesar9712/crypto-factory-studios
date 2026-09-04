from pathlib import Path


def test_worker_passes_through_conditional_asset_responses_without_body():
    worker = Path('worker/index.js').read_text(encoding='utf-8')
    assert "response.status===304" in worker
    assert "response.status===204" in worker
    assert "response.status===205" in worker
    assert "return new Response(null" in worker


def test_worker_handles_asset_binding_failures_without_cloudflare_1101():
    worker = Path('worker/index.js').read_text(encoding='utf-8')
    assert "response=await env.ASSETS.fetch(request)" in worker
    assert "Service temporarily unavailable" in worker
    assert "status:503" in worker
