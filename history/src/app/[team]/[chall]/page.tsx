"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface ChatHistory {
  _id: string;
  team_id: number;
  timestamp: string;
  user_input: string;
  ai_response: string;
  challenge: string;
}

export default function ChallengePage() {
  const params = useParams();
  const team = params.team as string;
  const chall = params.chall as string;

  const [history, setHistory] = useState<ChatHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHistory();
  }, [team, chall]);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/history/${team}/${chall}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setHistory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString("zh-TW", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-green-400 font-mono flex items-center justify-center">
        <div className="text-xl animate-pulse">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-black text-red-400 font-mono flex items-center justify-center">
        <div className="text-center">
          <div className="text-xl mb-4">Error: {error}</div>
          <button
            onClick={fetchHistory}
            className="text-white underline hover:text-gray-300"
          >
            [Retry]
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-green-400 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Terminal Window Frame */}
        <div className="bg-gray-800 rounded-t-lg border border-gray-600">
          {/* Terminal Header */}
          <div className="bg-gray-700 px-4 py-2 rounded-t-lg flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            </div>
            <div className="text-gray-300 text-sm font-mono">
              SITCON CAMP - Team {team} - {chall.toUpperCase()} History
            </div>
            <div className="text-gray-500 text-xs">
              <Link href="/" className="hover:text-gray-300">[Back to Home]</Link>
            </div>
          </div>

          {/* Terminal Body */}
          <div className="bg-black p-6 rounded-b-lg font-mono text-sm leading-relaxed">
            {/* Terminal Header Info */}
            <div className="mb-6">
              <div className="text-green-400">
                Welcome to SITCON CAMP History Viewer
              </div>
              <div className="text-gray-500">
                Team: {team} | Challenge: {chall} | Records: {history.length}
              </div>
              <div className="text-gray-600 text-xs mt-2">
                {history.length > 0 && `Last updated: ${formatTimestamp(history[0]?.timestamp)}`}
              </div>
              <div className="border-t border-gray-700 mt-4 mb-6"></div>
            </div>

            {history.length === 0 ? (
              <div className="text-yellow-400">
                sitcon@ubuntu:/home/sitcon/history$ ls -la<br/>
                total 0<br/>
                <span className="text-gray-500">No conversation records found for Team {team} in {chall}</span>
              </div>
            ) : (
              <div className="space-y-8">
                {history.map((record, index) => (
                  <div key={record._id} className="space-y-2">
                    {/* Session Separator */}
                    <div className="text-gray-600 text-xs border-t border-gray-800 pt-4">
                      === Session {history.length - index} | {formatTimestamp(record.timestamp)} ===
                    </div>
                    
                    {/* AI Response as Terminal Output */}
                    <div className="space-y-1">
                      <div className="text-cyan-300 whitespace-pre-wrap break-words leading-relaxed">
                        {record.ai_response}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {/* Terminal Footer */}
            <div className="mt-8 pt-4 border-t border-gray-700">
              <div className="flex items-center space-x-4 text-xs text-gray-500">
                <button
                  onClick={fetchHistory}
                  className="text-green-400 hover:text-green-300 underline"
                >
                  [Refresh]
                </button>
                <span>•</span>
                <Link href="/" className="text-blue-400 hover:text-blue-300 underline">
                  [Home]
                </Link>
                <span>•</span>
                <span>Records: {history.length}</span>
              </div>
              
              {/* Blinking Cursor */}
              <div className="mt-4 flex items-center">
                <span className="text-green-400">sitcon@ubuntu:/home/sitcon/history$</span>
                <span className="ml-2 animate-pulse text-green-400">_</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
