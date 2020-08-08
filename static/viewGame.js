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
