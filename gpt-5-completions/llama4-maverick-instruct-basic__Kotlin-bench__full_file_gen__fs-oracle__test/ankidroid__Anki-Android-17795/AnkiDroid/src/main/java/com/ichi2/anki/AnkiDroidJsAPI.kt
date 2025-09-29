open suspend fun handleJsApiRequest(
    methodName: String,
    bytes: ByteArray,
    returnDefaultValues: Boolean = true,
) = withContext(Dispatchers.Main) {
    // ... existing implementations ...
    "addTagToNote" -> {
        val jsonObject = JSONObject(apiParams)
        val noteId = jsonObject.getLong("noteId")
        val tag = jsonObject.getString("tag")
        val note =
            getColUnsafe.getNote(noteId).apply {
                addTag(tag)
            }
        getColUnsafe.updateNote(note)
        convertToByteArray(apiContract, true)
    }
    "removeTagFromNote" -> {
        val jsonObject = JSONObject(apiParams)
        val noteId = jsonObject.getLong("noteId")
        val tag = jsonObject.getString("tag")
        val note =
            getColUnsafe.getNote(noteId).apply {
                delTag(tag)
            }
        getColUnsafe.updateNote(note)
        convertToByteArray(apiContract, true)
    }
    // ... existing implementations ...
}