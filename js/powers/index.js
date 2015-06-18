$(document).ready(function() {
    $("a.remove_power").click(function() {
        $(this).parents("li").effect('highlight', {}, 10000);
        if (confirm("Remove this power?")) {
            return confirm("Are you sure you want to remove this power?  This action cannot be undone.");
        }
        return false;
    });
});
