import type { AppProps } from 'next/app'
import '@/styles/globals.css'
import Head from 'next/head'

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Head>
        <title>125 Build Automation Extend</title>
        <meta name="description" content="SaaS형 AI 허브 확장 버전" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <Component {...pageProps} />
    </>
  )
}
