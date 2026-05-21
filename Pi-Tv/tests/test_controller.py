from pitv.controller import BACK_TO_TV_LABEL, AppController
from pitv.m3u_parser import Channel
from pitv.models import Country


def _controller_with_channels() -> AppController:
    countries = [
        Country(name="United Kingdom", code="GB", flag="🇬🇧"),
        Country(name="Ireland", code="IE", flag="🇮🇪"),
    ]
    controller = AppController(countries)
    controller.view = "channels"
    controller.country = countries[0]
    controller.channels = [
        Channel(name="BBC One", url="", tvg_id="bbc1"),
        Channel(name="ITV", url="", tvg_id="itv"),
    ]
    return controller


def test_offer_resume_tv_shows_country_list_with_back_row() -> None:
    controller = _controller_with_channels()

    controller.offer_resume_tv(1)

    assert controller.view == "regions"
    assert controller.selected_index == 0
    assert controller.item_labels()[0] == BACK_TO_TV_LABEL
    assert controller.menu_to_country_index(0) is None
    assert controller.menu_to_country_index(1) == 0
    assert controller.menu_to_country_index(2) == 1


def test_take_resume_tv_returns_channel_and_restores_channels_view() -> None:
    controller = _controller_with_channels()
    controller.offer_resume_tv(1)

    resume = controller.take_resume_tv()

    assert resume == 1
    assert controller.view == "channels"
    assert controller.selected_index == 1
    assert controller.resume_tv_index() is None
    assert controller.item_labels() == ["BBC One", "ITV"]


def test_clear_resume_tv_removes_back_row() -> None:
    controller = _controller_with_channels()
    controller.offer_resume_tv(1)
    controller.clear_resume_tv()

    assert controller.resume_tv_index() is None
    assert BACK_TO_TV_LABEL not in controller.item_labels()


def test_menu_to_channel_index_maps_channel_rows() -> None:
    controller = _controller_with_channels()

    assert controller.menu_to_channel_index(0) == 0
    assert controller.menu_to_channel_index(1) == 1
    assert controller.menu_to_channel_index(2) is None
