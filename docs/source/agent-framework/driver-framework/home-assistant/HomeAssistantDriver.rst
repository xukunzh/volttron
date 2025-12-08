.. _HomeAssistant-Driver:

Home Assistant Driver
=====================

The Home Assistant driver enables VOLTTRON to read any data point from any Home Assistant controlled device.
Currently control (write access) is supported for lights (state and brightness), thermostats (state and temperature), 
switches, media players, and covers.

The following diagram shows interaction between platform driver agent and home assistant driver.

.. mermaid::

   sequenceDiagram
       HomeAssistant Driver->>HomeAssistant: Retrieve Entity Data (REST API)
       HomeAssistant-->>HomeAssistant Driver: Entity Data (Status Code: 200)
       HomeAssistant Driver->>PlatformDriverAgent: Publish Entity Data
       PlatformDriverAgent->>Controller Agent: Publish Entity Data

       Controller Agent->>HomeAssistant Driver: Instruct to Turn Off Light
       HomeAssistant Driver->>HomeAssistant: Send Turn Off Light Command (REST API)
       HomeAssistant-->>HomeAssistant Driver: Command Acknowledgement (Status Code: 200)

Pre-requisites
--------------
Before proceeding, find your Home Assistant IP address and long-lived access token from `here <https://developers.home-assistant.io/docs/auth_api/#long-lived-access-token>`_.

Clone the repository, start volttron, install the listener agent, and the platform driver agent.

- `Listener agent <https://volttron.readthedocs.io/en/main/introduction/platform-install.html#installing-and-running-agents>`_
- `Platform driver agent <https://volttron.readthedocs.io/en/main/agent-framework/core-service-agents/platform-driver/platform-driver-agent.html?highlight=platform%20driver%20isntall#configuring-the-platform-driver>`_

Supported Device Types
----------------------

The Home Assistant driver supports the following device types with write access:

**Lights**
  - Control state (on/off)
  - Control brightness (0-255)
  - Control RGB color

**Thermostats (Climate)**
  - Control state (off/heat/cool/auto)
  - Set target temperature

**Input Boolean**
  - Toggle state

**Switches**
  - Turn on/off

**Media Players**
  - Control playback (play/pause/stop)
  - Set volume level
  - Navigate tracks (next/previous)

**Covers**
  - Open/close
  - Set position (0-100)

All Home Assistant controlled devices support read access for their states and attributes.

Configuration
--------------

After cloning, generate configuration files. Each device requires one device configuration file and one registry file.
Ensure your registry_config parameter in your device configuration file, links to correct registry config name in the
config store. For more details on how volttron platform driver agent works with volttron configuration store see,
`Platform driver configuration <https://volttron.readthedocs.io/en/main/agent-framework/driver-framework/platform-driver/platform-driver.html#configuration-and-installation>`_
Examples for lights, thermostats, switches, media players, and covers are provided below.

Device configuration
++++++++++++++++++++

Device configuration file contains the connection details to you home assistant instance and driver_type as "home_assistant"

.. code-block:: json

   {
       "driver_config": {
           "ip_address": "Your Home Assistant IP",
           "access_token": "Your Home Assistant Access Token",
           "port": "Your Port"
       },
       "driver_type": "home_assistant",
       "registry_config": "config://light.example.json",
       "interval": 30,
       "timezone": "UTC"
   }

Registry Configuration
+++++++++++++++++++++++

Registry file can contain one single device and its attributes or a logical group of devices and its
attributes. Each entry should include the full entity id of the device, including but not limited to home assistant provided prefix
such as "light.", "climate.", "switch.", "media_player.", "cover.", etc. The driver uses these prefixes to convert states into integers.

Each entry in a registry file should also have a 'Entity Point' and a unique value for 'Volttron Point Name'. The 'Entity ID' maps to the device instance, the 'Entity Point' extracts the attribute or state, and 'Volttron Point Name' determines the name of that point as it appears in VOLTTRON.

Attributes can be located in the developer tools in the Home Assistant GUI.

.. image:: home-assistant.png


Example Light Registry
**********************

Below is an example file named light.example.json which has attributes of a single light instance with entity
id 'light.example':

.. code-block:: json

   [
       {
           "Entity ID": "light.example",
           "Entity Point": "state",
           "Volttron Point Name": "light_state",
           "Units": "On / Off",
           "Units Details": "on/off",
           "Writable": true,
           "Starting Value": true,
           "Type": "boolean",
           "Notes": "lights hallway"
       },
       {
           "Entity ID": "light.example",
           "Entity Point": "brightness",
           "Volttron Point Name": "light_brightness",
           "Units": "int",
           "Units Details": "light level",
           "Writable": true,
           "Starting Value": 0,
           "Type": "int",
           "Notes": "brightness control, 0 - 255"
       }
   ]


.. note::

When using a single registry file to represent a logical group of multiple physical entities, make sure the
"Volttron Point Name" is unique within a single registry file.

For example, if a registry file contains entities with
id  'light.instance1' and 'light.instance2' the entry for the attribute brightness for these two light instances could
have "Volttron Point Name" as 'light1/brightness' and 'light2/brightness' respectively. This would ensure that data
is posted to unique topic names and brightness data from light1 is not overwritten by light2 or vice-versa.

Example Thermostat Registry
****************************

For thermostats, the state is converted into numbers as follows: "0: Off, 2: heat, 3: Cool, 4: Auto",

.. code-block:: json

   [
       {
           "Entity ID": "climate.my_thermostat",
           "Entity Point": "state",
           "Volttron Point Name": "thermostat_state",
           "Units": "Enumeration",
           "Units Details": "0: Off, 2: heat, 3: Cool, 4: Auto",
           "Writable": true,
           "Starting Value": 1,
           "Type": "int",
           "Notes": "Mode of the thermostat"
       },
       {
           "Entity ID": "climate.my_thermostat",
           "Entity Point": "current_temperature",
           "Volttron Point Name": "volttron_current_temperature",
           "Units": "F",
           "Units Details": "Current Ambient Temperature",
           "Writable": true,
           "Starting Value": 72,
           "Type": "float",
           "Notes": "Current temperature reading"
       },
       {
           "Entity ID": "climate.my_thermostat",
           "Entity Point": "temperature",
           "Volttron Point Name": "set_temperature",
           "Units": "F",
           "Units Details": "Desired Temperature",
           "Writable": true,
           "Starting Value": 75,
           "Type": "float",
           "Notes": "Target Temp"
       }
   ]

Example Switch Registry
************************

Switches support binary on/off control. The state is represented as an integer: 0 for off, 1 for on.

.. code-block:: json

   [
       {
           "Entity ID": "switch.bedroom_light",
           "Entity Point": "state",
           "Volttron Point Name": "switch_state",
           "Units": "On / Off",
           "Units Details": "0: off, 1: on",
           "Writable": true,
           "Starting Value": 0,
           "Type": "int",
           "Notes": "Bedroom switch control"
       }
   ]

**Usage Example:**

.. code-block:: python

   # Turn on a switch
   agent.vip.rpc.call(
       'platform.driver',
       'set_point',
       'devices/BUILDING/ROOM/switch',
       'switch_state',
       1
   ).get()

   # Turn off a switch
   agent.vip.rpc.call(
       'platform.driver',
       'set_point',
       'devices/BUILDING/ROOM/switch',
       'switch_state',
       0
   ).get()

Example Media Player Registry
*******************************

Media players support playback control, volume adjustment, and track navigation. The playback state is represented as: 
0 for stop/off, 1 for pause, 2 for play.

.. code-block:: json

   [
       {
           "Entity ID": "media_player.living_room",
           "Entity Point": "state",
           "Volttron Point Name": "media_state",
           "Units": "Enumeration",
           "Units Details": "0: stop/off, 1: pause, 2: play",
           "Writable": true,
           "Starting Value": 0,
           "Type": "int",
           "Notes": "Media player playback state"
       },
       {
           "Entity ID": "media_player.living_room",
           "Entity Point": "volume_level",
           "Volttron Point Name": "media_volume",
           "Units": "Percentage",
           "Units Details": "0.0 to 1.0",
           "Writable": true,
           "Starting Value": 0.5,
           "Type": "float",
           "Notes": "Volume control"
       },
       {
           "Entity ID": "media_player.living_room",
           "Entity Point": "next_track",
           "Volttron Point Name": "media_next",
           "Units": "Action",
           "Units Details": "Any value triggers action",
           "Writable": true,
           "Type": "int",
           "Notes": "Skip to next track"
       },
       {
           "Entity ID": "media_player.living_room",
           "Entity Point": "previous_track",
           "Volttron Point Name": "media_previous",
           "Units": "Action",
           "Units Details": "Any value triggers action",
           "Writable": true,
           "Type": "int",
           "Notes": "Skip to previous track"
       }
   ]

**Usage Example:**

.. code-block:: python

   # Start playback
   agent.vip.rpc.call(
       'platform.driver',
       'set_point',
       'devices/BUILDING/ROOM/media_player',
       'media_state',
       2  # 2 = play
   ).get()

   # Pause playback
   agent.vip.rpc.call(
       'platform.driver',
       'set_point',
       'devices/BUILDING/ROOM/media_player',
       'media_state',
       1  # 1 = pause
   ).get()

   # Set volume to 50%
   agent.vip.rpc.call(
       'platform.driver',
       'set_point',
       'devices/BUILDING/ROOM/media_player',
       'media_volume',
       0.5
   ).get()

   # Skip to next track
   agent.vip.rpc.call(
       'platform.driver',
       'set_point',
       'devices/BUILDING/ROOM/media_player',
       'media_next',
       1
   ).get()

Example Cover Registry
***********************

Covers (curtains, blinds, garage doors) support open/close commands and position control. The state is a string 
("open", "closed", "opening", "closing") and position is an integer from 0 (closed) to 100 (open).

.. code-block:: json

   [
       {
           "Entity ID": "cover.garage_door",
           "Entity Point": "state",
           "Volttron Point Name": "cover_state",
           "Units": "Open / Closed",
           "Units Details": "String: open, closed, opening, closing",
           "Writable": true,
           "Type": "string",
           "Notes": "Cover state control"
       },
       {
           "Entity ID": "cover.garage_door",
           "Entity Point": "current_position",
           "Volttron Point Name": "cover_position",
           "Units": "Percentage",
           "Units Details": "0 to 100 (0=closed, 100=open)",
           "Writable": true,
           "Starting Value": 0,
           "Type": "int",
           "Notes": "Cover position control"
       }
   ]

**Usage Example:**

.. code-block:: python

   # Open cover
   agent.vip.rpc.call(
       'platform.driver',
       'set_point',
       'devices/BUILDING/ROOM/cover',
       'cover_state',
       'open'
   ).get()

   # Close cover
   agent.vip.rpc.call(
       'platform.driver',
       'set_point',
       'devices/BUILDING/ROOM/cover',
       'cover_state',
       'close'
   ).get()

   # Set position to 50%
   agent.vip.rpc.call(
       'platform.driver',
       'set_point',
       'devices/BUILDING/ROOM/cover',
       'cover_position',
       50
   ).get()

Storing Configuration
++++++++++++++++++++++

Transfer the registers files and the config files into the VOLTTRON config store using the commands below:

.. code-block:: bash

   vctl config store platform.driver light.example.json HomeAssistant_Driver/light.example.json
   vctl config store platform.driver devices/BUILDING/ROOM/light.example HomeAssistant_Driver/light.example.config

Upon completion, initiate the platform driver. Utilize the listener agent to verify the driver output:

.. code-block:: bash

   2023-09-12 11:37:00,226 (listeneragent-3.3 211531) __main__ INFO: Peer: pubsub, Sender: platform.driver:, Bus: , Topic: devices/BUILDING/ROOM/light.example/all, Headers: {'Date': '2023-09-12T18:37:00.224648+00:00', 'TimeStamp': '2023-09-12T18:37:00.224648+00:00', 'SynchronizedTimeStamp': '2023-09-12T18:37:00.000000+00:00', 'min_compatible_version': '3.0', 'max_compatible_version': ''}, Message:
   [{'light_brightness': 254, 'state': 'on'},
    {'light_brightness': {'type': 'integer', 'tz': 'UTC', 'units': 'int'},
     'state': {'type': 'integer', 'tz': 'UTC', 'units': 'On / Off'}}]

Running Tests
+++++++++++++++++++++++
To run tests on the VOLTTRON home assistant driver you need to create helpers in your home assistant instance. 

**Required Test Entities:**

1. **Toggle Helper**: Go to **Settings > Devices & services > Helpers > Create Helper > Toggle**. Name it **volttrontest**.
2. **Switch Entity**: A switch entity named **switch.test_switch**
3. **Media Player Entity**: A media player entity named **media_player.test_player**
4. **Cover Entity**: A cover entity named **cover.test_cover**

After creating these entities, run the pytest from the root of your VOLTTRON directory:

.. code-block:: bash

    pytest services/core/PlatformDriverAgent/tests/test_home_assistant.py

If everything works correctly, all tests should pass, including the new integration tests for switches, media players, and covers.
