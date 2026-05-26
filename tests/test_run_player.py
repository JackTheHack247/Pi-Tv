from pitv.controller import AppController
from pitv.models import Country


def test_run_player_without_channels_returns_menu() -> None:
    controller = AppController([Country(name="Test", code="XX", flag="")])

    result = controller.run_player(0)

    assert result == "menu"
