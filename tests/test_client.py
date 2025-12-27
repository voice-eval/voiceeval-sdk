import pytest
from voiceeval import Client

def test_client_init():
    client = Client(api_key="test")
    assert client.api_key == "test"
    assert client.api_key == "test"
