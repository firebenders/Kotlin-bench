enum class ViewerCommandCategory(val categoryId: Int, val displayStringResource: Int) {
    ANSWER_BUTTONS(R.id.answer_buttons, R.string.answer_buttons),
    FLAGS(R.id.flags, R.string.flags),
    WHITEBOARD(R.id.whiteboard, R.string.whiteboard),
    CARD(R.id.card, R.string.card),
    NAVIGATION(R.id.navigation, R.string.navigation),
    MISC(R.id.misc, R.string.misc);

    companion object {
        fun getCategoryById(id: Int): ViewerCommandCategory? {
            return values().find { it.categoryId == id }
        }
    }
}