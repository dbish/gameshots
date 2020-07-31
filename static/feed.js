var earliestSeen;
var postIDs;
var username; 
var following;

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

function addPosts(newPosts){
	console.log(newPosts);
	for (i in newPosts){
		if (!(postIDs.has(newPosts[i][6]))){
			addNewPost(newPosts[i]);
		}
	}
	earliestSeen = newPosts[newPosts.length-1][5];
}

function addNewPost(info){
	var pDisplay_name = info[11];
	var pUsername = info[0];
	var voted = info[9];


	postIDs.add(info[6]);
	var post = $('<div>').appendTo('#postsDiv'); 
	post.addClass("card bg-dark");
	if (info[8]){
		post.addClass('complete border border-warning');
	}
	post.attr('id', info[6]);

	var header = $('<div>').appendTo(post);
	header.addClass('card-header');
	var profileHTML = '';
	if (pDisplay_name != pUsername){
		profileHTML += pDisplay_name+' @';
	}
	profileHTML += '<a href="/gamer/'+info[0]+'">'+info[0]+'</a><i class="fa fa-gamepad"></i><i>'+info[1]+'</i>';
	header.append(profileHTML);
	header.append('<div class="coins">'+info[4]+'</div>');

	post.append('<a href="/post/'+info[6]+'"><img src="'+info[2]+'" class="card-img-top"></a>');

	var body = $('<div>').appendTo(post);
	body.addClass('card-body');
	
	if (voted){
		body.append('<button class="btn upvoteButton" onclick="upvotePost('+info[6]+')" style="display:none">+1</button>');
		body.append('<button class="btn downvoteButton" onclick="downvotePost('+info[6]+')">-1</button>');
	}else{
		body.append('<button class="btn upvoteButton" onclick="upvotePost('+info[6]+')">+1</button>');
		body.append('<button class="btn downvoteButton" onclick="downvotePost('+info[6]+')" style="display:none">-1</button>');
	}
	body.append('<button class="btn more"><i class="fa fa-ellipsis-h"></i></button>');
	
	var comments = $('<ul>').appendTo(body);
	comments.addClass('commentsList');
	comments.append('<li class="editorial">'+info[5]+': '+info[3]+'</li>');
	var comment;
	var li;
	for (i in info[7]){
		comment = info[7][i];
		li = $('<li>').appendTo(comments);
		if (comment[0] == username){
			li.addClass('mycomment');
			li.append('<button type="button" class="btn btn-sm btn-danger" onclick="deleteComment(\''+comment[3]+'\', this)">-</button>');
		}
		if (comment[0] == pUsername){
			li.append('<i class="fa fa-crown" style="color:yellow"></i>');
		}else if (following.has(comment[0])){
			li.append('<i class="fa fa-gem"></i>');
		}
		li.append('<a href="/gamer/'+comment[0]+'" style="color:'+comment[4]+'">'+comment[5]+'</a>: '+comment[1]);
	}

	var formBody = $('<div>').appendTo(post);
	formBody.addClass('card-body');
	var inputHTML = '<input class="commentbox" class="form-control" placeholder="enter comment..." ';
	inputHTML += 'onkeydown= "if (event.keyCode==13) \n';
	inputHTML += 'postComment(\''+info[6]+'\', \''+username+'\')">';
	formBody.append(inputHTML);
	formBody.append('<button class="btn" onclick="postComment(\''+info[6]+'\', \''+username+'\')">post</button>');
}

$(window).scroll(function (){
	if ($(document).height() - $(this).height() == $(this).scrollTop()) {
		console.log('getting more posts');
        $.ajax({
            url: '/scrollFeed?before='+earliestSeen,
            async: true,            // by default, it's async, but...
            dataType: 'json',       // or the dataType you are working with
            timeout: 10000,          // IMPORTANT! this is a 10 seconds timeout
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
