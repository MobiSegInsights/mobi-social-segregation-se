#
# This is the user-interface definition of a Shiny web application. You can
# run the application by clicking 'Run App' above.
#
# Find out more about building applications with Shiny here:
#
#    http://shiny.rstudio.com/
#

library(shiny)
library(mapdeck)
library(sf)
library(dplyr)
library(geojsonsf)

# Define UI for application that shows social segregation metrics on the map
fluidPage(

    # Application title
    titlePanel("Census statistics and income unevenness in Sweden (2019)"),
    
    # Sidebar with two radio buttons selecting metrics to show
    sidebarLayout(
        sidebarPanel(
            radioButtons("aspect", h4("Please select statistic:"),
                         choices = list('Foreign background' = 'Foreign background',
                                        'Lowest income group' = 'Lowest income group',
                                        "Income unevenness" = 'evenness_income'), 
                         selected = "Foreign background"),
            actionButton("execute", "Map it"),
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
            
            mapdeckOutput("segPlot", height = "600px", width="100%"),
            
            p("Data source: Statistics Sweden (SCB).",
              a("DeSO – Demografiska statistikområden", 
                href = "https://www.scb.se/hitta-statistik/regional-statistik-och-kartor/regionala-indelningar/deso---demografiska-statistikomraden/")),
        )
    )
)
