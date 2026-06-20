`timescale 1ns/1ps

module cryo_brain_decoder_visible_tb;
    logic clk;
    logic rst_n;
    logic syndromes_valid;
    logic [7:0] syndromes;
    logic corrections_valid;
    logic [3:0] corrections;
    logic [7:0] confidence;

    cryo_brain_decoder dut (
        .clk(clk),
        .rst_n(rst_n),
        .syndromes_valid(syndromes_valid),
        .syndromes(syndromes),
        .corrections_valid(corrections_valid),
        .corrections(corrections),
        .confidence(confidence)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    task automatic check_basic_decode;
        syndromes = 8'hA5;
        syndromes_valid = 1'b1;
        @(posedge clk);
        syndromes_valid = 1'b0;
        @(posedge clk);
        if (!corrections_valid) begin
            $display("SCENARIO basic_decode FAIL");
            $finish(1);
        end
        if (corrections !== (syndromes[3:0] ^ syndromes[7:4])) begin
            $display("SCENARIO basic_decode FAIL");
            $finish(1);
        end
        $display("SCENARIO basic_decode PASS");
    endtask

    initial begin
        rst_n = 0;
        syndromes_valid = 0;
        syndromes = 0;
        repeat (3) @(posedge clk);
        rst_n = 1;
        check_basic_decode();
        $finish(0);
    end
endmodule