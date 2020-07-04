function followUser(user){
	$.post('/follow', {
		'follow':user
	}).done(function(response){
		$('#followButton').hide();
		$('#unfollowButton').show();
		console.log('followed');
	}).fail(function(){
		console.log('failure contacting server');
	});
}

function unfollowUser(user){
	$.post('/unfollow',{
		'unfollow':user
	}).done(function(response){
		$('#unfollowButton').hide();
		$('#followButton').show();
	}).fail(function(){
		console.log('failure contacting server');
	});
}
