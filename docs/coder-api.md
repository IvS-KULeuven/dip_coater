# Coder API

The Coder tab lets you run simple Python scripts that control the dip coater.

Use this for repeatable routines such as:

- lower a sample or substrate into a dip coating solution
- wait for a fixed time
- withdraw a sample or substrate at a controlled speed
- wait for drying
- repeat the sequence

!!! warning
    Test new scripts with the dummy driver first. Then test with small distances and low speeds before using real coating hardware.

## Basic Script

This script lowers the moving assembly by 10 mm, waits 5 seconds, then raises it by 10 mm.

```python
self.enable_motor()

self.move_down(10, 5)
self.sleep(5)
self.move_up(10, 2)

self.disable_motor()
```

## Available Commands

### Enable the Motor

```python
self.enable_motor()
```

This arms the motor so it can move.

### Disable the Motor

```python
self.disable_motor()
```

This disables the motor. Use this at the end of a script.

### Move Down

```python
self.move_down(distance_mm, speed_mm_s, acceleration_mm_s2=None)
```

Examples:

```python
self.move_down(10, 5)
self.move_down(10, 5, 10)
```

The first example lowers the moving assembly by 10 mm at 5 mm/s. The second also sets acceleration to 10 mm/s^2.

### Move Up

```python
self.move_up(distance_mm, speed_mm_s, acceleration_mm_s2=None)
```

Examples:

```python
self.move_up(10, 5)
self.move_up(10, 5, 10)
```

### Home the Motor

```python
self.home_motor()
```

If you need to choose a direction explicitly:

```python
self.home_motor(home_up=True)
self.home_motor(home_up=False)
```

Homing is required before moving to an absolute position.

### Move to an Absolute Position

```python
self.move_to_position(position_mm, speed_mm_s=None, acceleration_mm_s2=None)
```

Examples:

```python
self.move_to_position(10)
self.move_to_position(10, 5)
self.move_to_position(10, 5, 10)
```

### Wait

```python
self.sleep(seconds)
```

Example:

```python
self.sleep(5)
```

## Example: Simple Dip Cycle

```python
self.enable_motor()

# Move into the liquid.
self.move_down(20, 4)

# Wait while submerged.
self.sleep(10)

# Withdraw slowly.
self.move_up(20, 1)

self.disable_motor()
```

## Example: Repeated Cycles

```python
self.enable_motor()

for cycle in range(3):
    self.move_down(15, 4)
    self.sleep(5)
    self.move_up(15, 2)
    self.sleep(10)

self.disable_motor()
```

## Loading Code From a File

In the Coder tab:

1. Type the path to a `.py` file.
2. Press `LOAD code from file`.
3. Check that the code appears in the editor.
4. Press `RUN code`.

The path must point to an existing Python file.
