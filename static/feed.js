function postComment(postID, user){
	console.log('test');
	var text = $('#'+postID).find('.commentbox').val();
	console.log(text)
	$.post('/postComment',{
		'text':text,
		'postID':postID
	}).done(function(response){
		console.log(text);
		addComment(postID, text, user);
	}).fail(function(){
		console.log('could not post comment');
	});
	console.log('done posting');
}

function addComment(postID, text, user){
	var commentsList = $('#'+postID).find('.commentsList');
	commentsList.append('<li><a href="/gamer/'+user+'">'+user+'</a>: '+text+'</li>');
}
