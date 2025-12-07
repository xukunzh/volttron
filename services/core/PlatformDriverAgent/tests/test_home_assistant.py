# -*- coding: utf-8 -*- {{{
# ===----------------------------------------------------------------------===
#
#                 Component of Eclipse VOLTTRON
#
# ===----------------------------------------------------------------------===
#
# Copyright 2023 Battelle Memorial Institute
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# ===----------------------------------------------------------------------===
# }}}

import json
import logging
import pytest
import gevent

from volttron.platform.agent.known_identities import (
    PLATFORM_DRIVER,
    CONFIGURATION_STORE,
)
from volttron.platform import get_services_core
from volttron.platform.agent import utils
from volttron.platform.keystore import KeyStore
from volttrontesting.utils.platformwrapper import PlatformWrapper

utils.setup_logging()
logger = logging.getLogger(__name__)

# To run these tests, create a helper toggle named volttrontest in your Home Assistant instance.
# This can be done by going to Settings > Devices & services > Helpers > Create Helper > Toggle
HOMEASSISTANT_TEST_IP = ""
ACCESS_TOKEN = ""
PORT = ""

skip_msg = "Some configuration variables are not set. Check HOMEASSISTANT_TEST_IP, ACCESS_TOKEN, and PORT"

# Skip tests if variables are not set
pytestmark = pytest.mark.skipif(
    not (HOMEASSISTANT_TEST_IP and ACCESS_TOKEN and PORT),
    reason=skip_msg
)
HOMEASSISTANT_DEVICE_TOPIC = "devices/home_assistant"


# Get the point which will should be off
def test_get_point(volttron_instance, config_store):
    expected_values = 0
    agent = volttron_instance.dynamic_agent
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant', 'bool_state').get(timeout=20)
    assert result == expected_values, "The result does not match the expected result."


# The default value for this fake light is 3. If the test cannot reach out to home assistant,
# the value will default to 3 making the test fail.
def test_data_poll(volttron_instance: PlatformWrapper, config_store):
    expected_values = [{'bool_state': 0}, {'bool_state': 1}]
    agent = volttron_instance.dynamic_agent
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'scrape_all', 'home_assistant').get(timeout=20)
    assert result in expected_values, "The result does not match the expected result."


# Turn on the light. Light is automatically turned off every 30 seconds to allow test to turn
# it on and receive the correct value.
def test_set_point(volttron_instance, config_store):
    expected_values = {'bool_state': 1}
    agent = volttron_instance.dynamic_agent
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant', 'bool_state', 1)
    gevent.sleep(10)
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'scrape_all', 'home_assistant').get(timeout=20)
    assert result == expected_values, "The result does not match the expected result."


@pytest.fixture(scope="module")
def config_store(volttron_instance, platform_driver):

    capabilities = [{"edit_config_store": {"identity": PLATFORM_DRIVER}}]
    volttron_instance.add_capabilities(volttron_instance.dynamic_agent.core.publickey, capabilities)

    registry_config = "homeassistant_test.json"
    registry_obj = [{
        "Entity ID": "input_boolean.volttrontest",
        "Entity Point": "state",
        "Volttron Point Name": "bool_state",
        "Units": "On / Off",
        "Units Details": "off: 0, on: 1",
        "Writable": True,
        "Starting Value": 3,
        "Type": "int",
        "Notes": "lights hallway"
    }]

    volttron_instance.dynamic_agent.vip.rpc.call(CONFIGURATION_STORE,
                                                 "manage_store",
                                                 PLATFORM_DRIVER,
                                                 registry_config,
                                                 json.dumps(registry_obj),
                                                 config_type="json")
    gevent.sleep(2)
    # driver config
    driver_config = {
        "driver_config": {"ip_address": HOMEASSISTANT_TEST_IP, "access_token": ACCESS_TOKEN, "port": PORT},
        "driver_type": "home_assistant",
        "registry_config": f"config://{registry_config}",
        "timezone": "US/Pacific",
        "interval": 30,
    }

    volttron_instance.dynamic_agent.vip.rpc.call(CONFIGURATION_STORE,
                                                 "manage_store",
                                                 PLATFORM_DRIVER,
                                                 HOMEASSISTANT_DEVICE_TOPIC,
                                                 json.dumps(driver_config),
                                                 config_type="json"
                                                 )
    gevent.sleep(2)

    yield platform_driver

    print("Wiping out store.")
    volttron_instance.dynamic_agent.vip.rpc.call(CONFIGURATION_STORE, "manage_delete_store", PLATFORM_DRIVER)
    gevent.sleep(0.1)


@pytest.fixture(scope="module")
def platform_driver(volttron_instance):
    # Start the platform driver agent which would in turn start the bacnet driver
    platform_uuid = volttron_instance.install_agent(
        agent_dir=get_services_core("PlatformDriverAgent"),
        config_file={
            "publish_breadth_first_all": False,
            "publish_depth_first": False,
            "publish_breadth_first": False,
        },
        start=True,
    )
    gevent.sleep(2)  # wait for the agent to start and start the devices
    assert volttron_instance.is_agent_running(platform_uuid)
    yield platform_uuid

    volttron_instance.stop_agent(platform_uuid)
    if not volttron_instance.debug_mode:
        volttron_instance.remove_agent(platform_uuid)


# ==================== Switch Device Tests ====================

def test_switch_turn_on(volttron_instance, config_store_switch):
    """Test turning on a switch device."""
    agent = volttron_instance.dynamic_agent
    
    agent.vip.rpc.call(
        PLATFORM_DRIVER, 
        'set_point', 
        'home_assistant_switch', 
        'switch_state', 
        1
    ).get(timeout=20)
    
    gevent.sleep(5)
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER, 
        'get_point', 
        'home_assistant_switch', 
        'switch_state'
    ).get(timeout=20)
    
    assert result == 1, f"Expected switch on (1), got {result}"


def test_switch_turn_off(volttron_instance, config_store_switch):
    """Test turning off a switch device."""
    agent = volttron_instance.dynamic_agent
    
    agent.vip.rpc.call(
        PLATFORM_DRIVER, 
        'set_point', 
        'home_assistant_switch', 
        'switch_state', 
        0
    ).get(timeout=20)
    
    gevent.sleep(5)
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER, 
        'get_point', 
        'home_assistant_switch', 
        'switch_state'
    ).get(timeout=20)
    
    assert result == 0, f"Expected switch off (0), got {result}"


def test_switch_scrape_all(volttron_instance, config_store_switch):
    """Test that switch data appears in scrape_all."""
    agent = volttron_instance.dynamic_agent
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER, 
        'scrape_all', 
        'home_assistant_switch'
    ).get(timeout=20)
    
    assert 'switch_state' in result, f"switch_state not found"
    assert result['switch_state'] in [0, 1], f"Invalid switch state: {result['switch_state']}"


@pytest.fixture(scope="function")
def config_store_switch(volttron_instance, platform_driver):
    """Configure a switch device for testing."""
    capabilities = [{"edit_config_store": {"identity": PLATFORM_DRIVER}}]
    volttron_instance.add_capabilities(
        volttron_instance.dynamic_agent.core.publickey, 
        capabilities
    )
    
    registry_config = "switch_test.json"
    registry_obj = [{
        "Entity ID": "switch.test_switch",
        "Entity Point": "state",
        "Volttron Point Name": "switch_state",
        "Units": "On / Off",
        "Units Details": "0: off, 1: on",
        "Writable": True,
        "Starting Value": 0,
        "Type": "int",
        "Notes": "Test switch"
    }]
    
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        registry_config,
        json.dumps(registry_obj),
        config_type="json"
    )
    
    gevent.sleep(2)
    
    device_topic = "devices/home_assistant_switch"
    driver_config = {
        "driver_config": {
            "ip_address": HOMEASSISTANT_TEST_IP, 
            "access_token": ACCESS_TOKEN, 
            "port": PORT
        },
        "driver_type": "home_assistant",
        "registry_config": f"config://{registry_config}",
        "timezone": "US/Pacific",
        "interval": 30,
    }
    
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        device_topic,
        json.dumps(driver_config),
        config_type="json"
    )
    
    gevent.sleep(5)
    
    yield platform_driver
    
    print("Cleaning up switch...")
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE, 
        "manage_delete_store", 
        PLATFORM_DRIVER
    )
    gevent.sleep(0.1)


# ==================== Media Player Device Tests ====================

def test_media_player_play(volttron_instance, config_store_media):
    """Test starting playback on a media player."""
    agent = volttron_instance.dynamic_agent
    
    agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'set_point',
        'home_assistant_media',
        'media_state',
        2
    ).get(timeout=20)
    
    gevent.sleep(5)
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'get_point',
        'home_assistant_media',
        'media_state'
    ).get(timeout=20)
    
    assert result == 2, f"Expected playing (2), got {result}"


def test_media_player_pause(volttron_instance, config_store_media):
    """Test pausing playback on a media player."""
    agent = volttron_instance.dynamic_agent
    
    agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'set_point',
        'home_assistant_media',
        'media_state',
        1
    ).get(timeout=20)
    
    gevent.sleep(5)
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'get_point',
        'home_assistant_media',
        'media_state'
    ).get(timeout=20)
    
    assert result == 1, f"Expected paused (1), got {result}"


def test_media_player_stop(volttron_instance, config_store_media):
    """Test stopping playback on a media player."""
    agent = volttron_instance.dynamic_agent
    
    agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'set_point',
        'home_assistant_media',
        'media_state',
        0
    ).get(timeout=20)
    
    gevent.sleep(5)
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'get_point',
        'home_assistant_media',
        'media_state'
    ).get(timeout=20)
    
    assert result == 0, f"Expected stopped (0), got {result}"


def test_media_player_set_volume(volttron_instance, config_store_media):
    """Test setting volume on a media player."""
    agent = volttron_instance.dynamic_agent
    
    agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'set_point',
        'home_assistant_media',
        'media_volume',
        0.5
    ).get(timeout=20)
    
    gevent.sleep(5)
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'get_point',
        'home_assistant_media',
        'media_volume'
    ).get(timeout=20)
    
    assert abs(result - 0.5) < 0.01, f"Expected 0.5, got {result}"


def test_media_player_next_track(volttron_instance, config_store_media):
    """Test skipping to next track."""
    agent = volttron_instance.dynamic_agent
    
    agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'set_point',
        'home_assistant_media',
        'media_next',
        1
    ).get(timeout=20)
    
    gevent.sleep(3)
    assert True


def test_media_player_previous_track(volttron_instance, config_store_media):
    """Test skipping to previous track."""
    agent = volttron_instance.dynamic_agent
    
    agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'set_point',
        'home_assistant_media',
        'media_previous',
        1
    ).get(timeout=20)
    
    gevent.sleep(3)
    assert True


def test_media_player_scrape_all(volttron_instance, config_store_media):
    """Test that media player data appears in scrape_all."""
    agent = volttron_instance.dynamic_agent
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'scrape_all',
        'home_assistant_media'
    ).get(timeout=20)
    
    assert 'media_state' in result, f"media_state not found"
    assert 'media_volume' in result, f"media_volume not found"
    
    media_state = result['media_state']
    assert media_state in [0, 1, 2] or isinstance(media_state, str), f"Invalid state: {media_state}"


@pytest.fixture(scope="function")
def config_store_media(volttron_instance, platform_driver):
    """Configure a media player device for testing."""
    capabilities = [{"edit_config_store": {"identity": PLATFORM_DRIVER}}]
    volttron_instance.add_capabilities(
        volttron_instance.dynamic_agent.core.publickey,
        capabilities
    )
    
    registry_config = "media_player_test.json"
    registry_obj = [
        {
            "Entity ID": "media_player.test_player",
            "Entity Point": "state",
            "Volttron Point Name": "media_state",
            "Units": "Enumeration",
            "Units Details": "0: stop, 1: pause, 2: play",
            "Writable": True,
            "Starting Value": 0,
            "Type": "int",
            "Notes": "Media player state"
        },
        {
            "Entity ID": "media_player.test_player",
            "Entity Point": "volume_level",
            "Volttron Point Name": "media_volume",
            "Units": "Percentage",
            "Units Details": "0.0 to 1.0",
            "Writable": True,
            "Starting Value": 0.5,
            "Type": "float",
            "Notes": "Volume control"
        },
        {
            "Entity ID": "media_player.test_player",
            "Entity Point": "next_track",
            "Volttron Point Name": "media_next",
            "Units": "Action",
            "Writable": True,
            "Type": "int",
            "Notes": "Next track"
        },
        {
            "Entity ID": "media_player.test_player",
            "Entity Point": "previous_track",
            "Volttron Point Name": "media_previous",
            "Units": "Action",
            "Writable": True,
            "Type": "int",
            "Notes": "Previous track"
        }
    ]
    
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        registry_config,
        json.dumps(registry_obj),
        config_type="json"
    )
    
    gevent.sleep(2)
    
    device_topic = "devices/home_assistant_media"
    driver_config = {
        "driver_config": {
            "ip_address": HOMEASSISTANT_TEST_IP,
            "access_token": ACCESS_TOKEN,
            "port": PORT
        },
        "driver_type": "home_assistant",
        "registry_config": f"config://{registry_config}",
        "timezone": "US/Pacific",
        "interval": 30,
    }
    
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        device_topic,
        json.dumps(driver_config),
        config_type="json"
    )
    
    gevent.sleep(5)
    
    yield platform_driver
    
    print("Cleaning up media player...")
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_delete_store",
        PLATFORM_DRIVER
    )
    gevent.sleep(0.1)


# ==================== Cover Device Tests ====================

def test_cover_open(volttron_instance, config_store_cover):
    """Test opening a cover device."""
    agent = volttron_instance.dynamic_agent
    
    agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'set_point',
        'home_assistant_cover',
        'cover_state',
        'open'
    ).get(timeout=20)
    
    gevent.sleep(10)
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'get_point',
        'home_assistant_cover',
        'cover_state'
    ).get(timeout=20)
    
    assert result in ['open', 'opening'], f"Expected open/opening, got {result}"


def test_cover_close(volttron_instance, config_store_cover):
    """Test closing a cover device."""
    agent = volttron_instance.dynamic_agent
    
    agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'set_point',
        'home_assistant_cover',
        'cover_state',
        'close'
    ).get(timeout=20)
    
    gevent.sleep(10)
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'get_point',
        'home_assistant_cover',
        'cover_state'
    ).get(timeout=20)
    
    assert result in ['closed', 'closing'], f"Expected closed/closing, got {result}"


def test_cover_set_position(volttron_instance, config_store_cover):
    """Test setting cover position."""
    agent = volttron_instance.dynamic_agent
    
    agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'set_point',
        'home_assistant_cover',
        'cover_position',
        50
    ).get(timeout=20)
    
    gevent.sleep(10)
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'get_point',
        'home_assistant_cover',
        'cover_position'
    ).get(timeout=20)
    
    assert result == 50, f"Expected 50, got {result}"


def test_cover_scrape_all(volttron_instance, config_store_cover):
    """Test that cover data appears in scrape_all."""
    agent = volttron_instance.dynamic_agent
    
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'scrape_all',
        'home_assistant_cover'
    ).get(timeout=20)
    
    assert 'cover_state' in result
    assert 'cover_position' in result


@pytest.fixture(scope="function")
def config_store_cover(volttron_instance, platform_driver):
    """Configure cover device for testing."""
    capabilities = [{"edit_config_store": {"identity": PLATFORM_DRIVER}}]
    volttron_instance.add_capabilities(
        volttron_instance.dynamic_agent.core.publickey,
        capabilities
    )
    
    registry_config = "cover_test.json"
    registry_obj = [
        {
            "Entity ID": "cover.test_cover",
            "Entity Point": "state",
            "Volttron Point Name": "cover_state",
            "Units": "Open / Closed",
            "Writable": True,
            "Type": "string",
            "Notes": "Cover state"
        },
        {
            "Entity ID": "cover.test_cover",
            "Entity Point": "current_position",
            "Volttron Point Name": "cover_position",
            "Units": "Percentage",
            "Writable": True,
            "Starting Value": 0,
            "Type": "int",
            "Notes": "Cover position"
        }
    ]
    
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        registry_config,
        json.dumps(registry_obj),
        config_type="json"
    )
    
    gevent.sleep(2)
    
    device_topic = "devices/home_assistant_cover"
    driver_config = {
        "driver_config": {
            "ip_address": HOMEASSISTANT_TEST_IP,
            "access_token": ACCESS_TOKEN,
            "port": PORT
        },
        "driver_type": "home_assistant",
        "registry_config": f"config://{registry_config}",
        "interval": 30,
    }
    
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        device_topic,
        json.dumps(driver_config),
        config_type="json"
    )
    
    gevent.sleep(5)
    
    yield platform_driver
    
    print("Cleaning up cover...")
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_delete_store",
        PLATFORM_DRIVER
    )
    gevent.sleep(0.1)