var earliestSeen;
var postIDs;
var following;

function toggleGame(game, e){
	$("."+game).each(function(){
		if (e.checked){
			$(this).show();
		}
		else {
			$(this).hide();
		}
	});
}

$(window).scroll(function (){
	if ($(document).height() - $(this).height() == $(this).scrollTop()) {
		console.log('getting more posts');
        $.ajax({
            url: '/scrollFeed?before='+earliestSeen,
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
