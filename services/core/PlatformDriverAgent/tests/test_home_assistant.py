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
    """
    Test turning on a switch device.
    
    Verifies that the set_point RPC call successfully turns on the switch
    and the state is correctly updated to 1 (on).
    """
    agent = volttron_instance.dynamic_agent
    
    # Turn on the switch
    agent.vip.rpc.call(
        PLATFORM_DRIVER, 
        'set_point', 
        'home_assistant_switch', 
        'switch_state', 
        1
    ).get(timeout=20)
    
    # Wait for the change to propagate
    gevent.sleep(5)
    
    # Verify the switch is on
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER, 
        'get_point', 
        'home_assistant_switch', 
        'switch_state'
    ).get(timeout=20)
    
    assert result == 1, f"Expected switch to be on (1), but got {result}"


def test_switch_turn_off(volttron_instance, config_store_switch):
    """
    Test turning off a switch device.
    
    Verifies that the set_point RPC call successfully turns off the switch
    and the state is correctly updated to 0 (off).
    """
    agent = volttron_instance.dynamic_agent
    
    # Turn off the switch
    agent.vip.rpc.call(
        PLATFORM_DRIVER, 
        'set_point', 
        'home_assistant_switch', 
        'switch_state', 
        0
    ).get(timeout=20)
    
    # Wait for the change to propagate
    gevent.sleep(5)
    
    # Verify the switch is off
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER, 
        'get_point', 
        'home_assistant_switch', 
        'switch_state'
    ).get(timeout=20)
    
    assert result == 0, f"Expected switch to be off (0), but got {result}"


def test_switch_scrape_all(volttron_instance, config_store_switch):
    """
    Test that switch data appears correctly in scrape_all results.
    
    Verifies that scrape_all includes the switch_state point with a valid value.
    """
    agent = volttron_instance.dynamic_agent
    
    # Get all data points
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER, 
        'scrape_all', 
        'home_assistant_switch'
    ).get(timeout=20)
    
    # Verify switch_state is in results
    assert 'switch_state' in result, \
        f"switch_state not found in scrape_all results. Got: {result.keys()}"
    
    # Verify the value is valid (0 or 1)
    switch_state = result['switch_state']
    assert switch_state in [0, 1], \
        f"Invalid switch state: {switch_state}. Expected 0 or 1"


# ==================== Config Store Fixture for Switch ====================

@pytest.fixture(scope="function")
def config_store_switch(volttron_instance, platform_driver):
    """
    Configure a switch device for testing.
    
    Creates registry and device configurations for a test switch,
    loads them into the config store, and cleans up after the test.
    
    Note: Requires a Home Assistant instance with a switch entity
    named 'switch.test_switch'. Update HOMEASSISTANT_TEST_IP, 
    ACCESS_TOKEN, and PORT at the top of this file.
    """
    capabilities = [{"edit_config_store": {"identity": PLATFORM_DRIVER}}]
    volttron_instance.add_capabilities(
        volttron_instance.dynamic_agent.core.publickey, 
        capabilities
    )
    
    # Registry configuration for switch
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
        "Notes": "Test switch device for integration testing"
    }]
    
    # Store registry config
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        registry_config,
        json.dumps(registry_obj),
        config_type="json"
    )
    
    gevent.sleep(2)
    
    # Device configuration
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
    
    # Store device config
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        device_topic,
        json.dumps(driver_config),
        config_type="json"
    )
    
    gevent.sleep(5)  # Wait for config to load
    
    yield platform_driver
    
    # Cleanup
    print("Cleaning up switch test configuration...")
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE, 
        "manage_delete_store", 
        PLATFORM_DRIVER
    )
    gevent.sleep(0.1)