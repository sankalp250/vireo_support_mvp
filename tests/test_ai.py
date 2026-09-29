from app.ai.mock import MockAIProvider

def test_mock_provider_schema():
    result=MockAIProvider().classify('Customer says the courier has not delivered the package. Agent raised a case with courier.','email')
    assert result.category=='Delivery & Shipping'
    assert 0 <= result.confidence <= 1
