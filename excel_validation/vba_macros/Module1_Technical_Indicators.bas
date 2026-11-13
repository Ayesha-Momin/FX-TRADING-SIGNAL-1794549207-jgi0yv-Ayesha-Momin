Attribute VB_Name = "Module1_Technical_Indicators"
' ==============================================================================
' FX Signal Lab - Technical Indicator Custom Functions
' ==============================================================================
Option Explicit

Public Function CalcRSI(PriceRange As Range, Optional Period As Integer = 14) As Double
    Dim i As Long, n As Long
    Dim Gains As Double, Losses As Double
    Dim Change As Double, RS As Double
    
    n = PriceRange.Rows.Count
    If n < Period + 1 Then
        CalcRSI = 50#
        Exit Function
    End If
    
    For i = 2 To Period + 1
        Change = PriceRange.Cells(i, 1).Value - PriceRange.Cells(i - 1, 1).Value
        If Change > 0 Then
            Gains = Gains + Change
        Else
            Losses = Losses + Abs(Change)
        End If
    Next i
    
    Gains = Gains / Period
    Losses = Losses / Period
    
    For i = Period + 2 To n
        Change = PriceRange.Cells(i, 1).Value - PriceRange.Cells(i - 1, 1).Value
        If Change > 0 Then
            Gains = (Gains * (Period - 1) + Change) / Period
            Losses = (Losses * (Period - 1)) / Period
        Else
            Gains = (Gains * (Period - 1)) / Period
            Losses = (Losses * (Period - 1) + Abs(Change)) / Period
        End If
    Next i
    
    If Losses = 0 Then
        CalcRSI = 100#
    Else
        RS = Gains / Losses
        CalcRSI = Round(100# - (100# / (1# + RS)), 2)
    End If
End Function

Public Function CalcEMA(CurrentPrice As Double, PrevEMA As Double, Optional Period As Integer = 20) As Double
    Dim Alpha As Double
    Alpha = 2# / (Period + 1#)
    CalcEMA = Round((CurrentPrice * Alpha) + (PrevEMA * (1# - Alpha)), 5)
End Function
