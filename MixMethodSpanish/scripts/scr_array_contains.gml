/// @function scr_array_contains(_array, _value)
/// @description Determine if value exists in array.
function scr_array_contains(_array, _value) {
    if (!is_array(_array)) {
        return false;
    }
    for (var i = 0; i < array_length(_array); i++) {
        if (_array[i] == _value) {
            return true;
        }
    }
    return false;
}
