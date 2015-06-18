$(document).ready(function() {
    $("a.remove_donation").click(function() {
        $(this).parents("tr").effect('highlight', {}, 10000);
        return confirm("Remove this donation?");
    });
});
