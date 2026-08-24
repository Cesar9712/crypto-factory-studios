from pathlib import Path
import json
from .repository import PaymentRepository
from .providers.tron_provider import MockTronProvider
from .services.payment_verifier import PaymentVerifier
from .services.payment_service import PaymentService

def build_mock_app(db_path=':memory:',clock=None):
    base=Path(__file__).parent
    config=json.loads((base/'config/treasury.mock.json').read_text())
    catalog=json.loads((base/'config/product_catalog.mock.json').read_text())
    repo=PaymentRepository(db_path); provider=MockTronProvider(); verifier=PaymentVerifier(config)
    return PaymentService(repo,provider,verifier,config,catalog,clock),repo,provider
