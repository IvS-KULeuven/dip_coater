# Python API

This page documents the reusable Python API for scripts and integrations.
The Textual UI widgets and low-level driver internals are intentionally not part of this public reference.

## App State

::: dip_coater.app_state.AppState

## Setup Profiles

::: dip_coater.setup_profiles.machine_profile.AvailableMachineSetups

::: dip_coater.setup_profiles.machine_profile.HomeDirection

::: dip_coater.setup_profiles.machine_profile.LimitSwitchSource

::: dip_coater.setup_profiles.machine_profile.LimitSwitchPolarity

::: dip_coater.setup_profiles.machine_profile.LimitSwitch

::: dip_coater.setup_profiles.machine_profile.LimitSwitchSetup

::: dip_coater.setup_profiles.machine_profile.LimitSwitchPair

::: dip_coater.setup_profiles.machine_profile.MachineProfile

::: dip_coater.setup_profiles.registry.list_machine_setups

::: dip_coater.setup_profiles.registry.get_default_setup_for_driver

::: dip_coater.setup_profiles.registry.get_machine_profile

::: dip_coater.setup_profiles.registry.create_custom_profile

## Mechanical Conversions

::: dip_coater.mechanical.mechanical_setup.MechanicalSetup

## Motor Drivers

::: dip_coater.motor_driver.motor_driver_interface.AvailableMotorDrivers

::: dip_coater.motor_driver.motor_driver_interface.MotorDriver

::: dip_coater.motor_driver.driver_registry.MotorDriverSpec

::: dip_coater.motor_driver.driver_registry.get_driver_spec

## Motion Control

::: dip_coater.services.motion_controller.MotionController

## Session Logging

::: dip_coater.logging.session_log.NullSessionLog

::: dip_coater.logging.session_log.SessionLog

## Helpers

::: dip_coater.get_version

::: dip_coater.config.config_loader.Config

::: dip_coater.config.config_loader.ConfigLoader

::: dip_coater.utils.helpers.clamp

::: dip_coater.utils.helpers.config_save_coder_filepath

::: dip_coater.utils.helpers.config_load_coder_filepath
