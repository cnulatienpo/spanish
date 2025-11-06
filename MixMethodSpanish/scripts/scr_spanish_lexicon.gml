/// @function scr_spanish_lexicon()
/// @description Provide a cached list of Spanish tokens including register hints.
function scr_spanish_lexicon() {
    static once = -1;
    if (once == -1) {
        global.__spanish_words = [
            "hola","adios","gracias","por","para","porque","pero","tambien","muy","mas","menos",
            "si","no","yo","tu","usted","el","ella","nosotros","ustedes","ellos",
            "me","te","se","lo","la","los","las","le","les","mi","su","sus","tu",
            "de","del","al","en","con","sin","sobre","entre","hasta","desde",
            "como","cuando","donde","quien","que","cual","cuanto",
            "ser","estar","tener","hacer","poder","ir","venir","quiero","puedo","tengo",
            "bien","mal","mucho","poco","aqui","alli","hoy","ayer","manana",
            // register hints
            "usted","ustedes","tu","tú","wey","carnal","güey","compa","mano","bro","vato"
        ];
        once = 1;
    }
    return global.__spanish_words;
}
