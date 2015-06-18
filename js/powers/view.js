$(document).ready(function() {
    $("#donation_from").autocomplete({ source: '/donors/list' });
    $("a.remove_donation").click(function() {
        return confirm("Remove this donation?");
    });

    function check_donor_exists() {
        $("#donor_exists").val(0);
        var name = $('#donation_from').val().trim();
        
        var url = '/donor/exists?name=' + name;
        $.getJSON(url, function(data) {
            if (!data) {
                if (confirm('Create new donor "' + name + '"?')) {
                    $(document).find('form').submit();
                }
            } else {
                $(document).find('form').submit();
            }
        });
    }

    validate = function() {
        $(".error_message").hide();
        var amount = $("#donation_amount").val().trim();
        $("#donation_amount").val(amount.replace(/,/g,'').replace(/^$/,''));
        var donor_not_empty = $("#donation_from").val().match(/\S/);
        var amount_not_empty = $("#donation_amount").val().match(/\S/);
        var amount_is_numeric = $("#donation_amount").val().match(/^[0-9.]+$/);
        var type_is_checked = $("#type_money:checked").val() || $("#type_food:checked").val()

        var valid = (donor_not_empty && amount_is_numeric && type_is_checked); 

        if (! donor_not_empty) {
            $("#donation_from").parents("div:first").find("span").show();
        }
        if (! amount_is_numeric) {
            $("#donation_amount").parents("div:first").find("span").show();
        }
        if (! type_is_checked) {
            $("#type_food").parents("div:first").find("span").show();
        }
        if (valid) {
            return check_donor_exists();
        }
        return false;
    };

    $("button.submit").click(validate);
});
