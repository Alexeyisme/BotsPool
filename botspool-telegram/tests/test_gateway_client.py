"""Unit tests for Gateway client"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.gateway.client import GatewayClient
from src.models import GraphUnavailableError


@pytest.fixture
def mock_state():
    """Fixture for mock state manager"""
    state = AsyncMock()
    state.token_needs_refresh.return_value = False
    state.get_token.return_value = "test_token"
    return state


@pytest.fixture
def gateway_client(mock_state):
    """Fixture for GatewayClient"""
    return GatewayClient("http://test-gateway:8000", mock_state)


@pytest.mark.asyncio
async def test_send_message_success(gateway_client, mock_state):
    """Test successful message sending"""
    # Mock HTTP response
    with patch.object(
        gateway_client.client, "post", new_callable=AsyncMock
    ) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Test response",
            "graph_type": "todo",
        }
        mock_post.return_value = mock_response

        result = await gateway_client.send_message(
            chat_id=12345, agent="todo", message="Test message", telegram_user_id=99999
        )

        assert result["response"] == "Test response"
        assert result["graph_type"] == "todo"


@pytest.mark.asyncio
async def test_send_message_graph_unavailable(gateway_client, mock_state):
    """Test handling of unavailable graph"""
    # Mock HTTP response with 503
    with patch.object(
        gateway_client.client, "post", new_callable=AsyncMock
    ) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_post.return_value = mock_response

        with pytest.raises(GraphUnavailableError):
            await gateway_client.send_message(
                chat_id=12345,
                agent="todo",
                message="Test message",
                telegram_user_id=99999,
            )


@pytest.mark.asyncio
async def test_ensure_valid_token_refresh(gateway_client, mock_state):
    """Test token refresh when needed"""
    # Mock token needs refresh
    mock_state.token_needs_refresh.return_value = True
    mock_state.get_refresh_token.return_value = "refresh_token"
    mock_state.get_token.return_value = "new_token"

    with patch("src.gateway.client.refresh_access_token") as mock_refresh:
        mock_refresh.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        }

        token = await gateway_client.ensure_valid_token(12345)

        assert token == "new_token"
        mock_state.store_tokens.assert_called_once()
