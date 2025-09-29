```kotlin
            ViewerCommand.RESCHEDULE_CARD -> {
                showRescheduleCardDialog()
                return true
            }
            else -> return super.executeCommand(which, fromGesture)
        }
    }

    private fun showRescheduleCardDialog() {
        val runnable = Consumer { days: Int ->
            val cardIds = listOf(currentCard!!.id)
            RescheduleCards(cardIds, days).runWithHandler(scheduleCollectionTaskHandler(R.plurals.reschedule_cards_dialog_acknowledge))
        }
        val dialog = rescheduleSingleCard(resources, currentCard!!, runnable)
        showDialogFragment(dialog)
    }
}
```