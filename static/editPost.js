function removeTag(tag){
	var toRemove = $('#'+tag);
	toRemove.parent().hide();
	toRemove.val('');
}

function addTag(){
	var tagList = $('#tagList');
	var len = $('#tagList li').length;
	var newInput = $('<input type="text" id="tag'+(len).toString()+'" name="tag'+(len).toString()+'" class="tag"> ');
	var deleteButton = $('<button onclick="removeTag(\'tag'+(len).toString()+'\')" type="button" class="btn btn-danger">-</button>');
	var newTag = $('<li>');
	
	newInput.autocomplete({
                source: autoCompleteTags,
                minLength: 3,
                select: function(event, ui){
                        console.log('selected:'+ui.item.value);
                }
        });
	newTag.append(newInput);
	newTag.append(deleteButton);

	tagList.append(newTag);
}

function autoCompleteTags(request, response){
			$.ajax({
				url: "/autocompleteTag",
				dataType: "json",
				data: {
					term: request.term
				},
				success: function(data){
					response(data);
				}
			});
}

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

	$('.tag').autocomplete({
		source: autoCompleteTags,
		minLength: 3,
		select: function(event, ui){
			console.log('selected:'+ui.item.value);
		}
	});
};
