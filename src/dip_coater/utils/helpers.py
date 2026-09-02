from json import dump, load, JSONDecodeError


def clamp(value, min_value, max_value):
    """Clamp a value between a minimum and maximum value.

    :param value: Value to constrain.
    :param min_value: Minimum allowed value.
    :param max_value: Maximum allowed value.
    :return: ``value`` constrained to the inclusive range.
    """
    return max(min(value, max_value), min_value)


def validated_number_from_submission(event, previous_value, number_type=float):
    """Return a validated numeric input value or restore its last good value.

    :param event: Textual input-submission event containing the validation result.
    :param previous_value: Last accepted value restored after invalid input.
    :param number_type: Callable used to convert the submitted text.
    :return: Converted number, or ``None`` when validation or conversion fails.
    """
    validation_result = getattr(event, "validation_result", None)
    if validation_result is None or not validation_result.is_valid:
        event.input.value = "" if previous_value is None else str(previous_value)
        return None
    try:
        return number_type(event.input.value)
    except (TypeError, ValueError):
        event.input.value = "" if previous_value is None else str(previous_value)
        return None


def config_save_coder_filepath(app_state, filepath: str):
    """Save the current coder script path to the app config file.

    :param app_state: Application state that provides the config-file path.
    :param filepath: Coder script path to store.
    """
    data = {"coder_filepath": filepath}
    with open(app_state.config.CONFIG_FILE, "w") as file:
        dump(data, file)


def config_load_coder_filepath(app_state):
    """Load the current coder script path from the app config file.

    :param app_state: Application state that provides the config-file path.
    :return: Stored coder script path, or an empty string when unavailable.
    """
    try:
        with open(app_state.config.CONFIG_FILE, "r") as file:
            data = load(file)
            return data.get("coder_filepath")
    except FileNotFoundError:
        return ""
    except JSONDecodeError:  # JSON file is empty or corrupted
        return ""
