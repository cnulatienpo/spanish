/// @function scr_spanish_ratio(_user)
/// @description Calculate Spanish token ratio in the user response.
/// @param {string} _user
function scr_spanish_ratio(_user) {
    var toks = scr_tokenize(_user);
    if (array_length(toks) == 0) {
        return 0;
    }
    var span = scr_count_spanish_tokens(_user, []);
    return span / array_length(toks);
}
