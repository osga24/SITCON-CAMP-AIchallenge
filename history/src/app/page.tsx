'use client'

import Link from 'next/link'

export default function Home() {
  const teams = Array.from({ length: 10 }, (_, i) => i + 1)
  const challenges = ['chall1', 'chall2', 'chall3']

  return (
    <div className="min-h-screen bg-gray-900 text-green-400 font-mono">
      <div className="max-w-6xl mx-auto p-8">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">SITCON CAMP - 歷史記錄查看器</h1>
          <p className="text-gray-400 text-lg">
            選擇團隊和挑戰來查看對話歷史記錄
          </p>
        </div>

        <div className="grid gap-8">
          {challenges.map((challenge) => (
            <div key={challenge} className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <h2 className="text-2xl font-bold mb-6 text-blue-300 text-center">
                {challenge.toUpperCase()}
              </h2>
              
              <div className="grid grid-cols-2 sm:grid-cols-5 md:grid-cols-10 gap-3">
                {teams.map((team) => (
                  <Link
                    key={team}
                    href={`/${team}/${challenge}`}
                    className="bg-gray-700 hover:bg-gray-600 border border-gray-600 hover:border-green-500 rounded-lg p-4 text-center transition-all duration-200 hover:scale-105"
                  >
                    <div className="text-lg font-semibold">
                      Team {team}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 text-center text-gray-500">
          <p>點擊任一團隊按鈕查看該團隊在指定挑戰中的對話記錄</p>
        </div>
      </div>
    </div>
  )
}
