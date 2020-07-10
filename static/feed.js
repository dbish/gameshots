function postComment(postID, user){
	var text = $('#'+postID).find('.commentbox').val();
	$.post('/postComment',{
		'text':text,
		'postID':postID
	}).done(function(response){
		var commentID = response; 
		addComment(postID, text, user, commentID);
	}).fail(function(){
		console.log('could not post comment');
	});
}

function addComment(postID, text, user, commentID){
	var commentsList = $('#'+postID).find('.commentsList');
	var newLI ='<li><a href="/gamer/'+user+'">'+user+'</a>: '+text;
	newLI += '<button type="button" class="btn btn-danger" onclick="deleteComment(\''+commentID+'\', this)">-</button>';
	newLI += '</li>';
	commentsList.append(newLI);

}

function deleteComment(commentID, e){
	$.post('/deleteComment', {
		'commentID':commentID
	}).done(function(response){
		$(e).parent().remove();
	}).fail(function(){
		console.log('failed to delete');
	});
}


function deletePost(postID){

	$.post('/deletePost', {
		'postID':postID
	}).done(function(response){

	}).fail(function(){
		console.log('failed to delete');
	});
}

function downvotePost(postID){
	var coins = $('#'+postID).find('.coins');
	var downvoteButton = $('#'+postID).find('.downvoteButton');
	var upvoteButton = $('#'+postID).find('.upvoteButton');

	$.post('/downvote', {
		'postID':postID
	}).done(function(response){
		coins.text(parseInt(coins.text())-1);
		downvoteButton.hide();
		upvoteButton.show();
		console.log('downvoted!');

	}).fail(function(){
		console.log('failed to downvote');
	});
}

function upvotePost(postID){
	var coins = $('#'+postID).find('.coins');
	var downvoteButton = $('#'+postID).find('.downvoteButton');
	var upvoteButton = $('#'+postID).find('.upvoteButton');
	

	$.post('/upvote', {
		'postID':postID
	}).done(function(response){
		coins.text(parseInt(coins.text())+1);
		upvoteButton.hide();
		downvoteButton.show();
		console.log('upvoted!');
	}).fail(function(){
		console.log('failed to vote');
	});
}

