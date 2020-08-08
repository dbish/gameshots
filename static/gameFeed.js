var earliestSeen;
var postIDs;
var following;


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

$(window).scroll(function (){
        if ($(document).height() - $(this).height() == $(this).scrollTop()) {
                console.log('getting more posts');
        $.ajax({
            url: '/scrollGamesFeed?before='+earliestSeen,
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
        profileHTML += '<a href="/gamer/'+info[0]+'">'+info[0]+'</a> <i class="fa fa-gamepad"></i> '
        profileHTML += '<a href="/game/'+info[10]+'"><i>'+info[1]+'</i></a>';
        header.append(profileHTML);
        header.append('<div class="coins">'+info[4]+'</div>');

        post.append('<a href="/post/'+info[6]+'"><img src="'+info[2]+'" class="card-img-top"></a>');

        var body = $('<div>').appendTo(post);
        body.addClass('card-body');

        if (voted){
                body.append('<button class="btn upvoteButton" onclick="upvotePost(\''+info[6]+'\')" style="display:none">+1</button>');
                body.append('<button class="btn downvoteButton" onclick="downvotePost(\''+info[6]+'\')">-1</button>');
        }else{
                body.append('<button class="btn upvoteButton" onclick="upvotePost(\''+info[6]+'\')">+1</button>');
                body.append('<button class="btn downvoteButton" onclick="downvotePost(\''+info[6]+'\')" style="display:none">-1</button>');
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
