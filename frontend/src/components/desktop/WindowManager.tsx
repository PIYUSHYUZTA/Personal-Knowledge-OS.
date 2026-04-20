import React from 'react'
import { useDesktopStore } from '@/store/useDesktopStore'
import Window from './Window'

export default function WindowManager() {
  const { windows } = useDesktopStore()
  
  return (
    <>
      {windows.map((win) => (
        <Window key={win.id} window={win} />
      ))}
    </>
  )
}
