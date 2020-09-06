var earliestSeen;
var postIDs;
var username;


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

function addPosts(newPosts){
        console.log(newPosts);
        for (i in newPosts){
                if (!(postIDs.has(newPosts[i][0]))){
                        addNewPost(newPosts[i]);
                }
        }
        earliestSeen = newPosts[newPosts.length-1][5];
}

function addNewPost(info){
	postIDs.add(info[0]);
        var post = $('<div>').appendTo('#postsDiv');
        post.addClass("card");
	var overlay = $('<div class="overlay">');
	var linkHTML =  '<a href="/post/'+info[0]+'"><i class="fa fa-share-square"></i></a>'
	overlay.append(linkHTML);
	post.append(overlay);

	if (info[1].includes('.twitch.tv') || info[1].includes('.youtube.com')){
		if (info[2] == 1){ 
			post.append('<iframe class="border border-warning card-img-top" src="'+info[1]+'" frameborder="0" scrolling="no" allowfullscreen="true"></iframe>');
		}else{
			post.append('<iframe class="card-img-top" src="'+info[1]+'" frameborder="0" scrolling="no" allowfullscreen="true"></iframe>');
		}
        }
        else if (info[1].includes('.mp4')){
		if (info[2] == 1){
			post.append('<video controls muted autoplay class="card-img-top border border-warning"><source src="'+info[1]+'" type="video/mp4"></video>');
		}else{
			post.append('<video controls muted autoplay class="card-img-top"><source src="'+info[1]+'" type="video/mp4"></video>');
		}
        }else{
		if (info[2] == 1){
			post.append('<img src="'+info[1]+'" class="card-img-top border border-warning">');
		}else{
			post.append('<img src="'+info[1]+'" class="card-img-top">');
		}
        }
}

$(window).scroll(function (){

        if ($(document).height() - $(this).height() == $(this).scrollTop()) {
                console.log('getting more posts');
        $.ajax({
            url: '/scrollUserProfile?before='+earliestSeen+'&user='+username,
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

