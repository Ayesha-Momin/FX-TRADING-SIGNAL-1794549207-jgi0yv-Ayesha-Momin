Attribute VB_Name = "Module3_Backtesting_Engine"
' ==============================================================================
' FX Signal Lab - VBA Institutional Backtest Engine
' ==============================================================================
Option Explicit

Public Sub RunAutomatedBacktest()
    Dim ws As Worksheet
    Dim LastRow As Long, i As Long
    Dim InTrade As Boolean, Direction As Integer
    Dim EntryPrice As Double, ExitPrice As Double
    Dim NetPnL As Double, TotalPnL As Double
    Dim WinTrades As Long, TotalTrades As Long
    
    Set ws = ActiveSheet
    LastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    If LastRow < 20 Then Exit Sub
    
    InTrade = False
    TotalPnL = 0#
    WinTrades = 0
    TotalTrades = 0
    
    For i = 21 To LastRow
        Dim Sig As Integer
        Sig = ws.Cells(i, "K").Value ' Direction Column
        
        If InTrade And (Sig <> Direction Or i = LastRow) Then
            ExitPrice = ws.Cells(i, "E").Value ' Close Price
            NetPnL = (ExitPrice - EntryPrice) * Direction * 100000# - 14# ' Deduct spread + commission
            TotalPnL = TotalPnL + NetPnL
            TotalTrades = TotalTrades + 1
            If NetPnL > 0 Then WinTrades = WinTrades + 1
            InTrade = False
        End If
        
        If Not InTrade And Sig <> 0 And i < LastRow Then
            InTrade = True
            Direction = Sig
            EntryPrice = ws.Cells(i, "E").Value
        End If
    Next i
    
    MsgBox "Backtest Finished!" & vbCrLf & _
           "Total Trades: " & TotalTrades & vbCrLf & _
           "Win Rate: " & Format(WinTrades / TotalTrades, "0.0%") & vbCrLf & _
           "Net PnL: $" & Format(TotalPnL, "#,##0.00"), vbInformation, "FX Signal Lab Backtest"
End Sub
