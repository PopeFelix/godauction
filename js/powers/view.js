$(document).ready(function() {
    $("#donation_from").autocomplete({ source: '/rpc?action=ListDonors' });
    $("a.remove_donation").click(function() {
        return confirm("Remove this donation?");
    });

    function parse_donor_name() {
        var name = $("#donation_from").val().trim();
        if (name.indexOf(' ') == -1) { // one word name
            return [ name ];
        }
        var split_name = name.split(' ');
        var last_name = split_name.pop(); // last name is one word
        var first_name = split_name.join(' '); // first name is everything else
        return [ first_name, last_name ];
    }

    function check_donor_exists() {
        $("#donor_exists").val(0);
        var names = parse_donor_name();
        var first_name = names[0];
        var last_name = names[1];
        var url = '/rpc?action=DonorExists&arg0="' + first_name + '"';
        if (last_name) {
            url = url + '&arg1="' + last_name + '"';
        }
        $.getJSON(url, function(data) {
            if (!data) {
                if (confirm('Create new donor "' + names.join(' ') + '"?')) {
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
