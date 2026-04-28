# Dip Coater User Guide

This guide explains how to install, start, and use the Dip Coater app. It is written for users who need to run the machine, not for software engineers.

The Dip Coater app lets you:

- move a sample or substrate down into and up out of a dip coating solution by a chosen distance
- set the speed and acceleration
- home the motor so the app knows the absolute position
- move to an absolute position after homing
- view motor and limit-switch status
- run repeatable coating routines from the Coder tab

## Recommended Reading Order

1. [Install the app](install.md)
2. [Connect the hardware](hardware-setup.md)
3. [Run the app](run-the-app.md)
4. [Use the interface](using-the-ui.md)
5. [Troubleshoot problems](troubleshooting.md)

If you only want to test the software without hardware, start with [Run the App](run-the-app.md) and use the dummy driver.

## Safety Basics

!!! warning
    The app controls a real motor. Keep fingers, samples, cables, tools, and coating vessels away from the moving parts before enabling the motor.

Before every coating run:

- check that the correct driver and setup profile are selected
- check that the moving assembly can travel through the intended coating path without hitting anything
- confirm that limit switches are connected if your setup uses them
- press `Stop and disable` if motion looks wrong

## What You Should See

The app opens inside a terminal window.

![Dip Coater main screen](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-dark.png)

The main screen has movement controls on the left and status information on the right.
