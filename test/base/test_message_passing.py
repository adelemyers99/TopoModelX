"""Test the message passing module."""
import pytest
import torch

from topomodelx.base.message_passing import MessagePassing
from topomodelx.utils.scatter import scatter


class AttentionMessagePassing(MessagePassing):
    """Custom class that inherits from MessagePassing to define attention."""

    def __init__(self, in_channels=None, att=False, initialization="xavier_uniform"):
        super().__init__(att=att, initialization=initialization)
        self.in_channels = in_channels
        if att:
            self.att_weight = torch.nn.Parameter(
                torch.Tensor(
                    2 * in_channels,
                )
            )


class TestMessagePassing:
    """Test the MessagePassing class."""

    def setup_method(self, method):
        """Make message_passing object."""
        self.mp = MessagePassing()
        self.attention_mp_xavier_uniform = AttentionMessagePassing(
            in_channels=2, att=True, initialization="xavier_uniform"
        )
        self.attention_mp_xavier_normal = AttentionMessagePassing(
            in_channels=2, att=True, initialization="xavier_normal"
        )

    def test_reset_parameters(self):
        """Test the reset of the parameters."""
        gain = 1.0
        with pytest.raises(RuntimeError):
            self.mp.initialization = "invalid"
            self.mp.reset_parameters(gain=gain)

        # Test xavier_uniform initialization
        self.mp.initialization = "xavier_uniform"
        self.mp.weight = torch.nn.Parameter(torch.Tensor(3, 3))
        self.mp.reset_parameters(gain=gain)
        assert self.mp.weight.shape == (3, 3)

        # Test xavier_normal initialization
        self.mp.initialization = "xavier_normal"
        self.mp.weight = torch.nn.Parameter(torch.Tensor(3, 3))
        self.mp.reset_parameters(gain=gain)
        assert self.mp.weight.shape == (3, 3)

    def custom_message(self, x):
        """Make custom message function."""
        return x

    def test_propagate(self):
        """Test propagate."""
        x = torch.tensor([[1, 2], [3, 4], [5, 6]])
        neighborhood = torch.sparse_coo_tensor(
            torch.tensor([[0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]]),
            torch.tensor([1, 2, 3, 4, 5, 6]),
            size=(3, 3),
        )
        self.mp.message = self.custom_message.__get__(self.mp)
        result = self.mp.propagate(x, neighborhood)
        expected_shape = (3, 2)
        assert result.shape == expected_shape

    def test_propagate_with_attention(self):
        """Test propagate with attention."""
        x = torch.tensor([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        neighborhood = torch.sparse_coo_tensor(
            torch.tensor([[0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]]),
            torch.tensor([1, 2, 3, 4, 5, 6]),
            size=(3, 3),
        )
        self.attention_mp_xavier_uniform.message = self.custom_message.__get__(self.mp)
        result = self.attention_mp_xavier_uniform.propagate(x, neighborhood)
        expected_shape = (3, 2)
        assert result.shape == expected_shape

        self.attention_mp_xavier_normal.message = self.custom_message.__get__(self.mp)
        result = self.attention_mp_xavier_normal.propagate(x, neighborhood)
        expected_shape = (3, 2)
        assert result.shape == expected_shape

    def test_sparsify_message(self):
        """Test sparsify_message."""
        x = torch.tensor(
            [
                [
                    1,
                    2,
                ],
                [3, 4],
                [5, 6],
            ]
        )
        neighborhood = torch.sparse_coo_tensor(
            torch.tensor([[0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]]),
            torch.tensor([1, 2, 3, 4, 5, 6]),
            size=(3, 3),
        )
        self.mp.message = self.custom_message.__get__(self.mp)
        _ = self.mp.propagate(x, neighborhood)
        x_sparse = self.mp.sparsify_message(x)
        expected = torch.tensor([[1, 2], [3, 4], [5, 6], [3, 4], [5, 6], [5, 6]])
        assert torch.allclose(x_sparse, expected)

    def test_get_x_i(self):
        """Test get_x_i."""
        x = torch.Tensor([[[1, 2, 3], [4, 5, 6], [7, 8, 9]]])
        self.mp.target_index_i = torch.LongTensor([1, 2, 0])
        result = self.mp.get_x_i(x)
        expected = torch.Tensor([[4, 5, 6], [7, 8, 9], [1, 2, 3]])
        assert torch.allclose(result, expected)

    def test_aggregate(self):
        """Test aggregate."""
        x = torch.tensor([[1, 2], [3, 4], [5, 6]])
        neighborhood = torch.sparse_coo_tensor(
            torch.tensor([[0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]]),
            torch.tensor([1, 2, 3, 4, 5, 6]),
            size=(3, 3),
        )
        neighborhood_values = neighborhood.coalesce().values()
        self.mp.message = self.custom_message.__get__(self.mp)
        _ = self.mp.propagate(x, neighborhood)
        x = self.mp.sparsify_message(x)
        x = neighborhood_values.view(-1, 1) * x
        result = self.mp.aggregate(x)
        expected = torch.tensor([[22, 28], [37, 46], [30, 36]])
        assert torch.allclose(result, expected)

    def test_forward(self):
        """Test forward."""
        x = torch.tensor([[1, 2], [3, 4], [5, 6]])
        neighborhood = torch.sparse_coo_tensor(
            torch.tensor([[0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]]),
            torch.tensor([1, 2, 3, 4, 5, 6]),
            size=(3, 3),
        )
        self.mp.message = self.custom_message.__get__(self.mp)
        result = self.mp.forward(x, neighborhood)
        expected_shape = (3, 2)
        assert result.shape == expected_shape
