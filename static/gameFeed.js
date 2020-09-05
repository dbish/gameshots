var earliestSeen;
var postIDs;
var following;


window.onload = function(){
        $('#game').autocomplete({
                source: function (request, response){
                        $.ajax({
                                url: "/autocompleteGames",
                                dataType: "json",
                                data: {
                                        term: request.term
                                },
                                success: function(data){
                                        response(data);
                                }
                        });
                },
                minLength: 2,
                select: function(event, ui){
                        console.log('selected:'+ui.item.value);
                }
        });
};

$(window).scroll(function (){
        if ($(document).height() - $(this).height() == $(this).scrollTop()) {
                console.log('getting more posts');
        $.ajax({
            url: '/scrollGamesFeed?before='+earliestSeen,
            async: true,
            dataType: 'json',
            timeout: 10000,
            cache: false

        }).done(function (data, textStatus, jqXHR) {
             // do something with data...
            if (data.length > 0){
                    addPosts(data);
            }
        }).fail(function(jqXHR, textStatus, errorThrown){
                console.log(textStatus);
        });
        }
});

