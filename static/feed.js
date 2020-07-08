function postComment(postID, user){
	console.log('test');
	var text = $('#'+postID).find('.commentbox').val();
	console.log(text)
	$.post('/postComment',{
		'text':text,
		'postID':postID
	}).done(function(response){
		console.log(text);
		console.log(response)
		var commentID = response; 
		addComment(postID, text, user, commentID);
	}).fail(function(){
		console.log('could not post comment');
	});
	console.log('done posting');
}

function addComment(postID, text, user, commentID){
	var commentsList = $('#'+postID).find('.commentsList');
	var newLI ='<li><a href="/gamer/'+user+'">'+user+'</a>: '+text;
	newLI += '<button type="button" class="btn btn-danger" onclick="deleteComment(\''+commentID+'\', this)">-</button>';
	newLI += '</li>';
	commentsList.append(newLI);

}

function deleteComment(commentID, e){
	console.log('deleting comment');
	$.post('/deleteComment', {
		'commentID':commentID
	}).done(function(response){
		$(e).parent().remove();
	}).fail(function(){
		console.log('failed to delete');
	});
}
