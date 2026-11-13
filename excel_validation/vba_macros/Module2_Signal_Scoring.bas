Attribute VB_Name = "Module2_Signal_Scoring"
' ==============================================================================
' FX Signal Lab - Multi-Factor Signal Scoring & Weighted Consensus
' ==============================================================================
Option Explicit

Public Function ComputeSignalScore(SMA_10 As Double, SMA_50 As Double, RSI As Double, _
                                   MACD_Hist As Double, BB_PctB As Double) As Double
    Dim SigMA As Double, SigRSI As Double, SigMACD As Double, SigBB As Double
    Dim WeightedScore As Double
    
    ' MA Trend Component
    If SMA_10 > SMA_50 Then SigMA = 1# Else If SMA_10 < SMA_50 Then SigMA = -1# Else SigMA = 0#
    
    ' RSI Momentum / Reversal
    If RSI < 30# Then
        SigRSI = 1#
    ElseIf RSI > 70# Then
        SigRSI = -1#
    ElseIf RSI > 55# Then
        SigRSI = 0.5
    ElseIf RSI < 45# Then
        SigRSI = -0.5
    Else
        SigRSI = 0#
    End If
    
    ' MACD Momentum
    If MACD_Hist > 0# Then SigMACD = 1# Else SigMACD = -1#
    
    ' Bollinger Oscillator
    If BB_PctB < 0.1 Then SigBB = 1# Else If BB_PctB > 0.9 Then SigBB = -1# Else SigBB = 0#
    
    ' Weighted Consensus
    WeightedScore = (SigMA * 0.25) + (SigRSI * 0.25) + (SigMACD * 0.3) + (SigBB * 0.2)
    ComputeSignalScore = Round(WeightedScore * 100#, 1)
End Function

Public Function EvaluateDirection(SignalScore As Double, Optional Threshold As Double = 25#) As Integer
    If SignalScore >= Threshold Then
        EvaluateDirection = 1  ' BUY
    ElseIf SignalScore <= -Threshold Then
        EvaluateDirection = -1 ' SELL
    Else
        EvaluateDirection = 0  ' FLAT / HOLD
    End If
End Function
