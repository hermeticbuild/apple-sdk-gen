#!/usr/bin/perl
# XNU's MakeInc.rule uses decomment FILE r only to check for empty output.
use strict;
use warnings;

my ($path, $mode) = @ARGV;
die "usage: $0 FILE r\n" unless @ARGV == 2 && $mode eq "r";
open my $file, '<:raw', $path or die "$path: $!\n";
local $/;
my $text = <$file> // "";
$text =~ s{ /\* .*? (?: \*/ | \z ) | // [^\n]* | /\z | [\x09-\x0d\x20]+ }{}gsx;
print "1\n" if length $text;
