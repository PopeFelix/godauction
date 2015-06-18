$(document).ready(function() {
    $("a.remove_donor").click(function() {
        $(this).parents("li").effect('highlight', {}, 10000);
        return confirm("Remove this donor?");
    });
});
