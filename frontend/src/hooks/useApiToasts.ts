import { useEffect } from 'react'
import { useToast } from '@/components/ui/Toast'
import { onApiToast } from '@/services/api'

/**
 * Hook that bridges the API layer's toast events into the React Toast system.
 * Mount this once at the app's authenticated shell level.
 */
export function useApiToasts() {
  const { addToast } = useToast()

  useEffect(() => {
    const unsubscribe = onApiToast((event) => {
      addToast({
        type: event.type,
        title: event.title,
        description: event.description,
      })
    })
    return unsubscribe
  }, [addToast])
}
