#
# This is the user-interface definition of a Shiny web application. You can
# run the application by clicking 'Run App' above.
#
# Find out more about building applications with Shiny here:
#
#    http://shiny.rstudio.com/
#

library(shiny)
library(leaflet)
library(dplyr)
library(sf)
library(ggplot2)
library(ggmap)
library(ggsn)
library(mapdeck)


# Define UI for application that draws a histogram
fluidPage(

    # Application title
    titlePanel("Residential social segregation in Sweden (2019)"),
    
    # Sidebar with a slider input for number of bins
    sidebarLayout(
        sidebarPanel(
            radioButtons("aspect", h4("Please select the segregation type:"),
                         choices = list("Net income" = 'income',
                                        'Foreign background' = 'background',
                                        'Region of birth' = 'birth_region'), 
                         selected = "income"),
            radioButtons("type", h4("Please select the measure:"),
                         choices = list("Evenness" = 'evenness',
                                        'Exposure' = 'isolation'), 
                         selected = "evenness"),
            submitButton("Map it!"),
            p(),
            p("Author: ",
              a("Yuan Liao", 
                href = "https://yuanliao.netlify.app")),
            p("Code generating the data: ",
              a("GitHub",
                href = "https://github.com/MobiSegInsights/mobi-social-segregation-se/blob/main/src/4-residential-segregation.ipynb"))
        ),

        # Show a plot of the generated distribution
        mainPanel(
            textOutput("selected_aspect"),
            
            textOutput("selected_type"),
            
            mapdeckOutput("segPlot", height = "800px", width="100%"),
            
            p("Data source: Statistics Sweden (SCB).",
              a("DeSO – Demografiska statistikområden", 
                href = "https://www.scb.se/hitta-statistik/regional-statistik-och-kartor/regionala-indelningar/deso---demografiska-statistikomraden/")),
        )
    )
)
