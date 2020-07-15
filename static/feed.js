var colors  = ['Aqua', 'Aquamarine', 'Blue', 'BlueViolet', 'Chartreuse', 'Coral', 'CornflowerBlue', 'Crimson',
	'Cyan', 'DarkMagenta', 'DarkOrange', 'Fuchsia', 'ForestGreen', 'Gold', 'GreenYellow',
	'HotPink', 'Lavender', 'LawnGreen', 'Lime', 'Magenta', 'MediumSpringGreen', 'Red', 'RoyalBlue', 'Yellow']

function getColor(name){
	var value = name.charCodeAt(0)*name.length;
	return colors[value%colors.length];
}

function postComment(postID, user){
	var commentBox = $('#'+postID).find('.commentbox');
	var text = commentBox.val();
	commentBox.val('');
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
	var newLI = '<li class="mycomment"><button type="button" class="btn btn-sm btn-danger" onclick="deleteComment(\''+commentID+'\', this)">-</button>';
	newLI +='<a href="/gamer/'+user+'" style="color:'+getColor(user)+'">'+user+'</a>: '+text;
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

