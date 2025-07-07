import { NextRequest, NextResponse } from 'next/server'
import { MongoClient } from 'mongodb'

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ team: string; chall: string }> }
) {
    try {
        const mongodb_url = process.env.MONGODB
        if (!mongodb_url) {
            console.error('MONGODB 環境變數未設置')
            return NextResponse.json(
                { error: '服務器配置錯誤' },
                { status: 500 }
            )
        }

        const { team, chall } = await params

        // 驗證參數
        const teamId = parseInt(team)
        if (isNaN(teamId) || teamId < 1 || teamId > 10) {
            return NextResponse.json(
                { error: '無效的團隊編號' },
                { status: 400 }
            )
        }

        // 連接 MongoDB
        const client = new MongoClient(mongodb_url)
        await client.connect()

        const db = client.db('sitcon_camp')
        const collection = db.collection(chall) // 使用 chall 參數作為集合名稱

        // 查詢該團隊的所有記錄，按時間排序
        const records = await collection
            .find({ team_id: teamId })
            .sort({ timestamp: -1 }) // 最新的在前面
            .toArray()

        await client.close()

        return NextResponse.json(records)

    } catch (error) {
        console.error('API 錯誤:', error)
        return NextResponse.json(
            { error: '服務器錯誤' },
            { status: 500 }
        )
    }
} 