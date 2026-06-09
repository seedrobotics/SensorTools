# SensorTools
A Standalone Python Package for using the singlex sensors. With examples on reading and saving the data and visualizing it.


## Install
It is recommended to use virtual environments for python tools to prevent dependency conflicts:

``` bash
python -m venv sensor_env
source sensor_env/bin/activate
pip install -r requirements.txt
```
If you don't want to use the gui you only need to install pyserial for reading the sensor data from the serial port.

## Use
The example program offers functions to write the sensor data to the terminal, to a csv, or to a udp port. Additionally it provides a gui for data visualization. The different modes can be selected via launch parameters.

``` bash
python SensorTool.py gui
```

For a full list of parameters check out
``` bash
python SensorTool.py -h
```

## Data Format
The data is published as strings of comma separated values to the serial port at a fixed frame rate. Each message starts with an @ followed by two columns of timesteps, if activated. Each PDC can be connected to up to 5 sensors at a time and every message published will have columns for each of the five sensors, no matter whether they are connected or not.

Each message follows this column layout:

| Column(s) | Meaning |
| --- | --- |
| `@` | Message start marker |
| Timestamp (s) | Timestamp in seconds, if activated |
| Timestamp (ms) | Timestamp in milliseconds, if activated |
| Sensor 1 — X, Y, Z | Three values for sensor 1 |
| Sensor 2 — X, Y, Z | Three values for sensor 2 |
| Sensor 3 — X, Y, Z | Three values for sensor 3 |
| Sensor 4 — X, Y, Z | Three values for sensor 4 |
| Sensor 5 — X, Y, Z | Three values for sensor 5 |

### Example
```
['@', '1781003060', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '1', '0', '1', '0', '0', '0', '']
```

### Useful commands
Commands can be issued as a serial write to the sensor port.

| Command | Description |
| --- | --- |
| `enabletime` | Enables timestamps |
| `disabletime` | Disables timestamps |
| `calibrate` | Calibrates all the sensors to 0 |
| `setepoch,[SECONDS],[MILLISECONDS]` | Sets the timestamps |
| `setperiod,[MILLISECONDS]` | Sets the output frame rate |

## Documentation
You can find the full documentation of the sensors in the [FTS3 Pressure Sensor knowledge base](https://kb.seedrobotics.com/doku.php?id=fts:fts3_pressuresensor).
