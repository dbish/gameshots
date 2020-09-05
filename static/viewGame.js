var earliestSeen;
var postIDs;
var following;
var game;

function followGame(game){
	$.post('/followGame', {
		'follow':game
	}).done(function(response){
		$('#followButton').hide();
		$('#unfollowButton').show();
		console.log('followed');
	}).fail(function(){
		console.log('failure contacting server');
	});
}

function unfollowGame(game){
	$.post('/unfollowGame',{
		'unfollow':game
	}).done(function(response){
		$('#unfollowButton').hide();
		$('#followButton').show();
	}).fail(function(){
		console.log('failure contacting server');
	});
}


$(window).scroll(function (){
        if ($(document).height() - $(this).height() == $(this).scrollTop()) {
                console.log('getting more posts');
        $.ajax({
            url: '/scrollViewGameFeed?before='+earliestSeen+'&game='+game,
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
